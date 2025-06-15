from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.db.models import Sum, Prefetch
from django.conf import settings
from django.contrib import messages
from collections import defaultdict
from django.http import HttpResponse, JsonResponse
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter
from django.contrib.auth.models import Group

from dashboards import utils
from reports.models import Answer, Report, SchoolReport, Section, Field, Year, SectionSreport
from schools.models import SchoolCloster, School, TerAdmin
from common.utils import get_cache_key

# Create your views here.
@login_required
def ter_admins_reports(request):
    reports = Report.objects.all().prefetch_related('reports', 'schools', 'schools__school', 'sections')

    return render(request, "dashboards/ter_admins_reports.html", {
        'reports': reports,
    })

#@cache_page(None, key_prefix="flow")
@login_required
@csrf_exempt
def ter_admins_dash(request):
    # Check if the user is a TerAdmin representatives
    ter_admins = TerAdmin.objects.filter(representatives=request.user)

    if not ter_admins.first():
        ter_admins = TerAdmin.objects.all()

    closters = SchoolCloster.objects.all()
    ed_levels = {
        'A': "1 — 11 классы",
        'M': "1 — 9 классы",
        'S': "1 — 4 классы",
        'MG': "5 — 11 классы",
        'G': "10 — 11 классы",
    }
    years = Year.objects.all().order_by('-year')
    
    year = Year.objects.get(is_current=True)
    schools_reports = None
    sections = None
    school_reports_data = {}
    stats = {}
    overall_stats = {}
    sections_data = {}
    fields_sum_data = {}
    show_ter_status = False
    filter_params = {}
    schools = School.objects.filter(ter_admin__in=ter_admins, is_archived=False)
    reports = Report.objects.filter(year=year)
  
    if request.method == 'POST':
        year = request.POST["year"]
        year = Year.objects.get(year=year)
        show_ter_status = 'show_ter_status' in request.POST
        reports = Report.objects.filter(year=year)
        sections = Section.objects.filter(report__in=reports).distinct('number').order_by('number')
        
        # Фильтруем отчеты в зависимости от статуса согласования

        if show_ter_status:
            schools_reports = SchoolReport.objects.filter(
                report__in=reports,
                status__in=['A', 'D']  # Показываем и принятые, и на согласовании
            ).order_by('school__name').prefetch_related('answers', 'sections')
        else:
            schools_reports = SchoolReport.objects.filter(
                report__in=reports,
                status='D'  # Только принятые
            ).order_by('school__name').prefetch_related('answers', 'sections')
        
        stats, overall_stats = utils.calculate_stats(year, schools_reports, sections)
        
        # Фильтруем школы по выбранным параметрам
        ter_admins_f = request.POST.get("ter_admin", '')
        if ter_admins_f and ter_admins_f != 'all':
            schools = schools.filter(ter_admin=ter_admins_f)
            filter_params['ter_admin'] = ter_admins_f
        elif ter_admins_f == 'all':
            # Если выбрано "Все управления/департаменты", не фильтруем школы
            filter_params['ter_admin'] = 'all'
            
        closters_f = request.POST.getlist("closters")
        if closters_f:
            schools = schools.filter(closter__in=closters_f)
            filter_params['closters'] = closters_f
            
        ed_levels_f = request.POST.getlist("ed_levels")
        if ed_levels_f:
            schools = schools.filter(ed_level__in=ed_levels_f)
            filter_params['ed_levels'] = ed_levels_f
            
        # Фильтруем отчеты по отфильтрованным школам
        schools_reports = schools_reports.filter(school__in=schools)
        if 'download' in request.POST:
            return utils.generate_ter_admins_report_csv(year, schools, schools_reports)

    # Generate cache key based on filters
    cache_key = get_cache_key('ter_admins_dash', 
        year=year,
        show_ter_status=show_ter_status,
        schools=','.join(sorted(str(s.id) for s in schools)),
        reports=','.join(sorted(str(r.id) for r in reports)) if reports else '',
        ter_admin=filter_params.get('ter_admin', ''),
        closters=','.join(sorted(filter_params.get('closters', []))),
        ed_levels=','.join(sorted(filter_params.get('ed_levels', [])))
    )
    
    # Try to get cached data
    cached_data = cache.get(cache_key)
    if cached_data and reports:  # Проверяем наличие reports
        # Фильтруем отчеты по статусу согласования, если это необходимо
        if show_ter_status:
            cached_data['schools_reports'] = cached_data['schools_reports'].filter(
                status__in=['A', 'D']
            )
        else:
            cached_data['schools_reports'] = cached_data['schools_reports'].filter(
                status='D'
            )
            
        return render(request, "dashboards/ter_admins_dash.html", {
            **cached_data,
            "years": years,
            "selected_year": year,
            "filter": filter_params,
            'ter_admins': ter_admins,
            'closters': closters,
            'ed_levels': ed_levels,
            'show_ter_status': show_ter_status
        })

    # If no cached data, perform the expensive calculations
    if reports:
        schools_reports = SchoolReport.objects.filter(
            report__in=reports,
            school__in=schools,
            status__in=['A', 'D'] if show_ter_status else ['D']
        ).select_related(
            'school',
            'report',
            'school__ter_admin',
        ).prefetch_related(
            'answers',
            'sections__section__fields',
            'sections__section',
        )
    else:
        schools_reports = SchoolReport.objects.none()

    school_reports_data = {}
    fields_data = {}
    sections = Section.objects.filter(report__in=reports).distinct('number').order_by('number').prefetch_related('fields') if reports else []

    for s_report in schools_reports:
        school_reports_data[s_report.id] = {
            'green_zone_answers': 0,
            'yellow_zone_answers': 0,
            'red_zone_answers': 0,
            'answers': 0
        }
        
        # Create lookup dict for answers
        answer_lookup = {a.question_id: a for a in s_report.answers.all()}
        
        for section in s_report.sections.all():
            if section.section.number not in fields_data:
                fields_data[section.section.number] = {
                    'fields': {}
                }
            section_number = section.section.number
            school_reports_data[s_report.id][section_number] = {
                'points': section.points,
                'zone': section.zone,
                'fields': {}
            }
            
            fields = sorted(
                section.section.fields.all(), 
                key=lambda x: [int(n) for n in str(x.number).split('.')]
            )
            
            for field in fields:
                if field.number not in fields_data[section_number]['fields']:
                    fields_data[section_number]['fields'][field.number] = {
                        'points': 0,
                        'green_zone': 0,
                        'yellow_zone': 0,
                        'red_zone': 0
                    }
                answer = answer_lookup.get(field.id)
                if answer:
                    school_reports_data[s_report.id][section_number]['fields'][field.number] = {
                        'points': answer.points,
                        'zone': answer.zone
                    }
    
                    fields_data[section_number]['fields'][field.number]['points'] += answer.points
                    school_reports_data[s_report.id]['answers'] += 1
                    if answer.zone == 'G':
                        school_reports_data[s_report.id]['green_zone_answers'] += 1
                        fields_data[section_number]['fields'][field.number]['green_zone'] += 1
                    elif answer.zone == 'Y':
                        school_reports_data[s_report.id]['yellow_zone_answers'] += 1
                        fields_data[section_number]['fields'][field.number]['yellow_zone'] += 1
                    elif answer.zone == 'R':
                        school_reports_data[s_report.id]['red_zone_answers'] += 1
                        fields_data[section_number]['fields'][field.number]['red_zone'] += 1
                else:
                    school_reports_data[s_report.id][section_number]['fields'][field.number] = {
                        'points': 0,
                        'zone': 'W'
                    }

    stats, overall_stats = utils.calculate_stats(year, schools_reports, sections)
    sections_data = {}

    sections_data = {}
    for section in sections:
        sections_objs = Section.objects.filter(name=section.name)
        fields = Field.objects.filter(sections__in=sections_objs).distinct('number').prefetch_related('answers')
        sections_data[section.number] = {
            'name': section.name,
            'fields': sorted(fields, key=lambda x: [int(n) for n in str(x.number).split('.')])
        }
    fields_sum_data = {}
    # fields = Field.objects.filter(sections__in=sections).distinct('number').prefetch_related('answers')
    for key, section in sections_data.items():
        for field in section['fields']:
            fields_sum_data[field.id] = field.answers.filter(s_report__in=schools_reports).aggregate(Sum('points'))['points__sum'] or 0

    # Prepare data for caching
    cache_data = {
        'reports': reports,
        'schools_reports': schools_reports,
        'sections': sections,
        'stats': stats,
        'overall_stats': overall_stats,
        'school_reports_data': school_reports_data,
        'fields_data': fields_data,
        'sections_data': sections_data,
        'fields_sum_data': fields_sum_data
    }

    # Cache the data for 10 minutes
    cache.set(cache_key, cache_data, timeout=600)

    # Проверяем, является ли пользователь администратором или представителем МинОбр
    try:
        mo_group = Group.objects.get(name='Представитель МинОбр')
        is_mo_or_admin = request.user.is_superuser or request.user.groups.filter(id=mo_group.id).exists()
    except Group.DoesNotExist:
        is_mo_or_admin = request.user.is_superuser

    return render(request, "dashboards/ter_admins_dash.html", {
        **cache_data,
        "years": years,
        "selected_year": year,
        "filter": filter_params,
        'ter_admins': ter_admins,
        'closters': closters,
        'ed_levels': ed_levels,
        'show_ter_status': show_ter_status
    })


@login_required
@csrf_exempt
def school_report(request):
    # Определяем, является ли пользователь директором школы
    is_school_principal = hasattr(request.user, 'school') and request.user.school
    
    # Получаем доступные ТУ/ДО
    ter_admins = TerAdmin.objects.filter(representatives=request.user).prefetch_related('schools')
    if not ter_admins.first():
        ter_admins = TerAdmin.objects.all().prefetch_related('schools')
    
    years = Year.objects.all().order_by('-year')
    
    school = None
    s_reports = None
    sections = None
    section_data = {}
    stats = {}
    filter_params = {}
    reports = None
    fields_sum_data = {}

    # Если пользователь - директор школы, автоматически используем его школу
    if is_school_principal:
        school = request.user.school
        
        # Берем последний год по умолчанию или годы из запроса
        if request.method == 'POST' and 'years' in request.POST:
            f_years = request.POST.getlist("years")
            f_years = [Year.objects.get(year=year) for year in f_years]
        else:
            current_year = years.first()
            if current_year:
                f_years = [current_year]
            else:
                f_years = []
        
        if f_years:
            reports = Report.objects.filter(year__in=f_years)
            sections = Section.objects.filter(report__in=reports).distinct('number').order_by('number')
            s_reports = SchoolReport.objects.filter(
                report__in=reports, 
                school=school, 
                status='D'
            ).order_by('report__year').prefetch_related('answers', 'sections')
            
            filter_params = {
                'years': f_years,
                'school': str(school.id),
                'ter_admin': str(school.ter_admin.id) if school.ter_admin else None
            }
            
            # Handle export request
            if request.method == 'POST' and 'download' in request.POST:
                return utils.generate_school_report_csv(f_years[-1], school, s_reports, sections)
            
            stats, section_data = utils.calculate_stats_and_section_data(f_years, reports, sections, s_reports)

            # Calculate fields sum data only for existing answers
            sections = Section.objects.filter(report__in=reports).distinct('number').order_by('number')
            fields = Field.objects.filter(sections__in=sections).distinct('number').prefetch_related('answers')
            
            for field in fields:
                answers_sum = field.answers.filter(
                    s_report__in=s_reports,
                    points__isnull=False
                ).aggregate(Sum('points'))['points__sum']
                fields_sum_data[field.id] = answers_sum if answers_sum is not None else 0
    # Если это не директор школы, обрабатываем GET и POST запросы стандартно
    else:
        # Проверяем, передан ли идентификатор школы в GET-параметрах
        if request.method == 'GET' and 'school' in request.GET:
            try:
                school_id = int(request.GET.get('school'))
                school = School.objects.get(id=school_id)
            except (ValueError, School.DoesNotExist):
                school = None

            # Если школа определена, автоматически формируем отчет
            if school:
                # Берем последний год по умолчанию
                current_year = years.first()
                if current_year:
                    f_years = [current_year]
                    reports = Report.objects.filter(year__in=f_years)
                    sections = Section.objects.filter(report__in=reports).distinct('number').order_by('number')
                    s_reports = SchoolReport.objects.filter(
                        report__in=reports, 
                        school=school, 
                        status='D'
                    ).order_by('report__year').prefetch_related('answers', 'sections')
                    
                    filter_params = {
                        'years': f_years,
                        'school': str(school.id),
                        'ter_admin': str(school.ter_admin.id) if school.ter_admin else None
                    }
                    
                    stats, section_data = utils.calculate_stats_and_section_data(f_years, reports, sections, s_reports)

                    # Calculate fields sum data only for existing answers
                    sections = Section.objects.filter(report__in=reports).distinct('number').order_by('number')
                    fields = Field.objects.filter(sections__in=sections).distinct('number').prefetch_related('answers')
                    
                    for field in fields:
                        answers_sum = field.answers.filter(
                            s_report__in=s_reports,
                            points__isnull=False
                        ).aggregate(Sum('points'))['points__sum']
                        fields_sum_data[field.id] = answers_sum if answers_sum is not None else 0

        # Обработка POST запроса (выбор фильтров)
        if request.method == 'POST' and not is_school_principal:
            school = School.objects.get(id=request.POST["school"])
            f_years = request.POST.getlist("years")
            f_years = [Year.objects.get(year=year) for year in f_years]
            reports = Report.objects.filter(year__in=f_years)
            sections = Section.objects.filter(report__in=reports).distinct('number').order_by('number')
            s_reports = SchoolReport.objects.filter(
                report__in=reports, 
                school=school, 
                status='D'
            ).order_by('report__year').prefetch_related('answers', 'sections')
            
            filter_params = {
                'years': f_years,
                'school': str(school.id),
                'ter_admin': str(school.ter_admin.id) if school.ter_admin else None
            }
            
            # Handle export request
            if 'download' in request.POST:
                return utils.generate_school_report_csv(f_years[-1], school, s_reports, sections)
                
            stats, section_data = utils.calculate_stats_and_section_data(f_years, reports, sections, s_reports)

            # Calculate fields sum data only for existing answers
            sections = Section.objects.filter(report__in=reports).distinct('number').order_by('number')
            fields = Field.objects.filter(sections__in=sections).distinct('number').prefetch_related('answers')
            
            for field in fields:
                answers_sum = field.answers.filter(
                    s_report__in=s_reports,
                    points__isnull=False
                ).aggregate(Sum('points'))['points__sum']
                fields_sum_data[field.id] = answers_sum if answers_sum is not None else 0

    # Подготавливаем список школ для выбора в зависимости от роли пользователя
    schools_for_select = []
    if is_school_principal:
        schools_for_select = [request.user.school]
    else:
        # Для остальных пользователей показываем все доступные школы
        for ter_admin in ter_admins:
            schools_for_select.extend(ter_admin.schools.filter(is_archived=False))

    return render(request, "dashboards/school_report.html", {
        "filter": filter_params,
        "ter_admins": ter_admins,
        "years": years,
        "schools": schools_for_select,
        "sections": sections,
        "section_data": section_data,
        "stats": stats,
        "fields_sum_data": fields_sum_data,
        "s_reports": s_reports,
        "dash_school": school
    })


# @cache_page(60 * 5, key_prefix="closters_report")
@login_required
@csrf_exempt
def closters_report(request, year=2024):
    filter_params = {}
    years = Year.objects.all().order_by('-year')
    if years:
        current_year = years[0]
    else:
        print("Ошибка: нет годов в базе!")
        current_year = Year.objects.get(is_current=True)

    # --- Инициализация переменных и справочников ---
    show_ter_status = False  # По умолчанию не показываем согласование

    # Доступные территориальные управления для пользователя
    ter_admins = TerAdmin.objects.filter(representatives=request.user)
    if not ter_admins.first():
        ter_admins = TerAdmin.objects.all()

    # Для админа и представителей МинОбр доступ ко всем ТУ/ДО
    ter_admins_for_schools = ter_admins
    if request.user.is_superuser or request.user.groups.filter(name='Представитель МинОбр').exists():
        ter_admins_for_schools = TerAdmin.objects.all()
        filter_params['ter_admin'] = 'all'

    # Справочники
    closters = SchoolCloster.objects.all()
    ed_levels = {
        'A': "1 — 11 классы",
        'M': "1 — 9 классы",
        'S': "1 — 4 классы",
        'MG': "5 — 11 классы",
        'G': "10 — 11 классы",
    }

    # Базовый queryset школ (далее будет фильтроваться)
    schools = School.objects.filter(
        ter_admin__in=ter_admins_for_schools,
        is_archived=False
    ).select_related('ter_admin', 'closter')

    # --- Отладочная информация ---

    is_mo_or_admin = request.user.is_superuser or request.user.groups.filter(name='Представитель МинОбр').exists()

    # ------------------------------------------------------------
    # Формирование данных отчёта
    # ------------------------------------------------------------

    # Определяем выбранный год (selected_year) для шаблона
    selected_year = current_year if request.method != 'POST' else Year.objects.get(year=year)

    # Запрашиваем отчёты школ с учётом статуса согласования
    s_reports_qs = SchoolReport.objects.filter(
        report__year=selected_year,
        status__in=['A', 'D'] if show_ter_status else ['D'],
        school__in=schools
    ).select_related(
        'school', 'school__ter_admin', 'school__closter'
    ).prefetch_related('sections__section', 'answers')

    # --- Секции и поля ---
    sections_src = Section.objects.filter(report__year=selected_year).order_by('number').prefetch_related('fields')

    # Уникальные номера секций (на случай дублей)
    seen_numbers = set()
    sections = []  # формат [(num, name, fields_qs)]
    for sec in sections_src:
        if sec.number in seen_numbers:
            continue
        seen_numbers.add(sec.number)
        sections.append((sec.number, sec.name, sec.fields.all().order_by('number')))

    # Для графика – списки номеров и названий
    section_numbers = [str(item[0]) for item in sections]
    section_names = [f"{item[0]}. {item[1]}" for item in sections]

    # --- Формируем словарь значений по школам ---
    school_values: dict[str, list[float]] = {}
    # Подготовим шаблон списка с нулями нужной длины
    zero_template = [0.0] * len(sections)

    # Предзагрузим SectionSreport для всех отчётов, чтобы не делать N+1
    ssr_qs = SectionSreport.objects.filter(s_report__in=s_reports_qs).select_related('section')
    # Индексация: {(report_id, section_number): points}
    ssr_dict = { (ssr.s_report_id, ssr.section.number): ssr.points for ssr in ssr_qs }

    for s_report in s_reports_qs:
        school_name = str(s_report.school)
        values = zero_template.copy()
        for idx, (num, _name, _fields) in enumerate(sections):
            points = ssr_dict.get((s_report.id, num), 0)
            values[idx] = float(points) if points is not None else 0.0
        school_values[school_name] = values

    # ------------------------------------------------------------
    # Формируем контекст и рендерим шаблон
    # ------------------------------------------------------------

    context = {
        'years': years,
        'ter_admins': ter_admins,
        'closters': closters,
        'ed_levels': ed_levels,
        's_reports': s_reports_qs,
        'sections': sections,
        'schools': schools,
        'filter': filter_params,
        'show_ter_status': show_ter_status,
        'selected_year': selected_year,
        'section_names': section_names,
        'section_numbers': section_numbers,
        'school_values': school_values,
        'is_mo_or_admin': is_mo_or_admin,
    }

    return render(request, "dashboards/closters_report.html", context)


# ===== Временные заглушки для отсутствующих представлений =====

@login_required
@csrf_exempt
def answers_distribution_report(request):
    """Временная заглушка. Полная реализация будет добавлена позже."""
    return HttpResponse("Отчёт в разработке.")


@login_required
@csrf_exempt
def get_schools_by_ter_admin(request):
    """Простой JSON со списком школ выбранного ТУ/ДО."""
    ter_admin_id = request.GET.get('ter_admin')
    schools_qs = School.objects.filter(ter_admin_id=ter_admin_id, is_archived=False) if ter_admin_id else School.objects.none()
    data = [{'id': s.id, 'name': str(s)} for s in schools_qs]
    return JsonResponse({'schools': data})
