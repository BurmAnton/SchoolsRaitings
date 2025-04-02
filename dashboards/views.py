from decimal import Decimal
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.db.models import Sum, Max
from django.conf import settings
from django.contrib import messages
import hashlib
import json
from django.http import JsonResponse, Http404, HttpResponse
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter

from dashboards import utils
from reports.models import Answer, Report, SchoolReport, Section, Field, Year, Option
from schools.models import SchoolCloster, School, TerAdmin
from common.utils import get_cache_key

# Create your views here.
@login_required
def ter_admins_reports(request):
    reports = Report.objects.all().prefetch_related('reports', 'schools', 'schools__school', 'sections')

    return render(request, "dashboards/ter_admins_reports.html", {
        'reports': reports,
    })


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://localhost:6379',
        'OPTIONS': {
            'db': '2',
        }
    }
}

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
    filter = {}
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
        if ter_admins_f:
            schools = schools.filter(ter_admin=ter_admins_f)
            filter['ter_admin'] = ter_admins_f
            
        closters_f = request.POST.getlist("closters")
        if closters_f:
            schools = schools.filter(closter__in=closters_f)
            filter['closters'] = closters_f
            
        ed_levels_f = request.POST.getlist("ed_levels")
        if ed_levels_f:
            schools = schools.filter(ed_level__in=ed_levels_f)
            filter['ed_levels'] = ed_levels_f
            
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
        ter_admin=filter.get('ter_admin', ''),
        closters=','.join(sorted(filter.get('closters', []))),
        ed_levels=','.join(sorted(filter.get('ed_levels', [])))
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
            "filter": filter,
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

    return render(request, "dashboards/ter_admins_dash.html", {
        **cache_data,
        "years": years,
        "selected_year": year,
        "filter": filter,
        'ter_admins': ter_admins,
        'closters': closters,
        'ed_levels': ed_levels,
        'show_ter_status': show_ter_status
    })


@login_required
@csrf_exempt
def school_report(request):
    ter_admins = TerAdmin.objects.filter(representatives=request.user).prefetch_related('schools')
    if not ter_admins.first():
        ter_admins = TerAdmin.objects.all().prefetch_related('schools')
    years = Year.objects.all().order_by('-year')
    
    school = None
    s_reports = None
    sections = None
    section_data = {}
    stats = {}
    filter = {}
    reports = None
    fields_sum_data = {}

    if request.method == 'POST':
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
        
        filter = {
            'years': f_years,
            'school': str(school.id),
            'ter_admin': str(school.ter_admin.id)
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

    return render(request, "dashboards/school_report.html", {
        'years': years,
        'ter_admins': ter_admins,
        'dash_school': school,
        's_reports': s_reports,
        'filter': filter,
        'sections': sections,
        'stats': stats,
        'section_data': section_data,
        'fields_sum_data': fields_sum_data
    })


@cache_page(None, key_prefix="closters_report")
@login_required
@csrf_exempt
def closters_report(request, year=2024):
    # Generate cache key based on request parameters
    cache_key = get_cache_key('closters_report_data',
        year=request.POST.get('year', year),
        ter_admin=request.POST.get('ter_admin', ''),
        closters=','.join(sorted(request.POST.getlist('closters', []))),
        ed_levels=','.join(sorted(request.POST.getlist('ed_levels', []))),
        show_ter_status=request.POST.get('show_ter_status', False)
    )
    
    # Try to get cached data
    cached_data = cache.get(cache_key)
    if cached_data:
        return render(request, "dashboards/closters_report.html", cached_data)

    ter_admins = TerAdmin.objects.filter(representatives=request.user)
    if not ter_admins.first():
        ter_admins = TerAdmin.objects.all()
    
    years = Year.objects.all().order_by('-year')
    closters = SchoolCloster.objects.all()
    ed_levels = {
        'A': "1 — 11 классы",
        'M': "1 — 9 классы",
        'S': "1 — 4 классы",
        'MG': "5 — 11 классы",
        'G': "10 — 11 классы",
    }
    
    schools = School.objects.filter(ter_admin__in=ter_admins, is_archived=False).select_related('ter_admin')
    filter = {}
    show_ter_status = False
    
    # Get initial year
    try:
        current_year = years[0]
    except IndexError as e:
        print(f"Ошибка при получении текущего года: {str(e)}")
        current_year = Year.objects.get(is_current=True)
        
    if request.method == 'POST':
        year = int(request.POST.get("year", current_year))
        year = Year.objects.get(year=year)
        show_ter_status = 'show_ter_status' in request.POST
        ter_admin_f = request.POST.get("ter_admin", '')
        if ter_admin_f:
            schools = schools.filter(ter_admin=ter_admin_f)
            filter['ter_admin'] = ter_admin_f
            
        closters_f = request.POST.getlist("closters")
        if closters_f:
            schools = schools.filter(closter__in=closters_f)
            filter['closters'] = closters_f
            
        ed_levels_f = request.POST.getlist("ed_levels")
        if ed_levels_f:
            schools = schools.filter(ed_level__in=ed_levels_f)
            filter['ed_levels'] = ed_levels_f
    else:
        year = current_year
        schools = schools.filter(ter_admin__name="Центральное управление")
    if 'download' in request.POST:
        s_reports = SchoolReport.objects.filter(
            report__year=year,
            status__in=['A', 'D'] if show_ter_status else ['D'],
            school__in=schools
        )
        return utils.generate_closters_report_csv(year, schools, s_reports)

    # Optimize sections and fields query
    sections_data = Section.objects.filter(
        report__year=year
    ).values(
        'number', 
        'name'
    ).distinct('number').order_by('number')

    sections_list = []
    for section in sections_data:
        section_objs = Section.objects.filter(
            name=section['name'], 
            report__year=year
        )
        fields = Field.objects.filter(
            sections__in=section_objs
        ).distinct().prefetch_related(
            'answers__s_report'
        ).select_related()
        
        sections_list.append([
            section['number'],
            section['name'],
            fields
        ])

    # Prepare data for caching
    context_data = {
        'years': years,
        'ter_admins': ter_admins,
        'closters': closters,
        'ed_levels': ed_levels,
        's_reports': SchoolReport.objects.filter(
            report__year=year,
            status__in=['A', 'D'] if show_ter_status else ['D'],
            school__in=schools
        ).select_related('school', 'report'),
        'sections': sections_list,
        'schools': schools,
        'filter': filter,
        'show_ter_status': show_ter_status
    }

    # Cache the data for 5 minutes
    cache.set(cache_key, context_data, timeout=300)

    return render(request, "dashboards/closters_report.html", context_data)

@csrf_exempt
@login_required
def answers_distribution_report(request):
    """
    Представление для отчета о распределении зон (красная, жёлтая, зелёная) 
    по территориальным управлениям (ТУ/ДО) с возможностью фильтрации по годам.
    """
    # Получаем доступные годы и территориальные управления для пользователя
    years = Year.objects.all().order_by('-year')
    ter_admins = TerAdmin.objects.filter(representatives=request.user)
    if not ter_admins.exists():
        ter_admins = TerAdmin.objects.all()
    
    # Подготовка контекста для фильтра
    filter_context = {
        'years': years,
        'ter_admins': ter_admins,
    }
    
    # Статистика по умолчанию (пустая)
    stats = []
    selected_years = []
    show_year_column = False
    
    # Инициализируем переменные для статистики, используемые в Excel-выгрузке
    section_stats = []
    cluster_stats = []
    indicator_stats = []
    
    # --- DEBUG START ---
    print(f"Request method: {request.method}")
    print(f"Session selected_year_ids before processing: {request.session.get('selected_year_ids')}")
    if request.method == 'POST':
        print(f"POST data years: {request.POST.getlist('years')}")
    # --- DEBUG END ---

    # Обработка запроса с фильтрами или установка всех годов по умолчанию
    if request.method == 'POST':
        # Получаем выбранные годы из POST-запроса
        year_ids = request.POST.getlist('years')
        if year_ids:
            selected_years = Year.objects.filter(id__in=year_ids).order_by('-year')
            # Показываем столбец "Год" только если выбрано больше одного года
            show_year_column = len(selected_years) > 1
            # Сохраняем выбранные годы в сессию
            request.session['selected_year_ids'] = year_ids
        else:
            # Если годы не выбраны, используем все годы без столбца "Год"
            selected_years = years
            show_year_column = False
            # Очищаем сессию
            if 'selected_year_ids' in request.session:
                del request.session['selected_year_ids']
    else: # Обработка GET-запроса
        # Проверяем, есть ли сохраненные годы в сессии
        if 'selected_year_ids' in request.session:
            year_ids = request.session.get('selected_year_ids')
            selected_years = Year.objects.filter(id__in=year_ids).order_by('-year')
            show_year_column = len(selected_years) > 1
        else:
            # По умолчанию используем все годы без столбца "Год"
            selected_years = years
            show_year_column = False
    
    # --- DEBUG START ---
    print(f"Final selected_years: {[y.year for y in selected_years]}")
    print(f"Final show_year_column: {show_year_column}")
    print(f"Session selected_year_ids after processing: {request.session.get('selected_year_ids')}")
    # --- DEBUG END ---
    
    # Если есть выбранные годы, рассчитываем статистику
    if selected_years:
        # Если не нужно показывать столбец "Год", агрегируем данные по всем годам
        if not show_year_column:
            # Рассчитываем статистику для всех лет вместе
            ter_admin_stats = {} # Словарь для агрегации данных по ТУ/ДО
            
            # Получаем отчеты для всех выбранных годов
            reports = Report.objects.filter(year__in=selected_years, is_published=True)
            
            # Получаем отчеты школ, которые были приняты (статус 'D')
            schools_reports = SchoolReport.objects.filter(
                report__in=reports,
                status='D'  # Только принятые отчеты
            )
                
            # Подсчитываем отчеты по зонам для каждого ТУ/ДО
            for report in schools_reports:
                # Пропускаем отчеты без школы или с архивной школой
                if not report.school or report.school.is_archived:
                    continue
                
                ter_admin_id = report.school.ter_admin_id
                
                # Инициализируем словарь для ТУ/ДО, если его еще нет
                if ter_admin_id not in ter_admin_stats:
                    ter_admin = TerAdmin.objects.get(id=ter_admin_id)
                    ter_admin_stats[ter_admin_id] = {
                        'ter_admin_id': ter_admin_id,
                        'ter_admin_name': ter_admin.name,
                        'red_zone': 0,
                        'yellow_zone': 0,
                        'green_zone': 0,
                        'total': 0
                    }
                
                # Увеличиваем счетчик для соответствующей зоны
                if report.zone == 'R':
                    ter_admin_stats[ter_admin_id]['red_zone'] += 1
                elif report.zone == 'Y':
                    ter_admin_stats[ter_admin_id]['yellow_zone'] += 1
                elif report.zone == 'G':
                    ter_admin_stats[ter_admin_id]['green_zone'] += 1
                
                # Увеличиваем общий счетчик отчетов для ТУ/ДО
                ter_admin_stats[ter_admin_id]['total'] += 1
                
            # Рассчитываем проценты для каждого ТУ/ДО
            for ter_admin_id in ter_admin_stats:
                item = ter_admin_stats[ter_admin_id]
                if item['total'] > 0:
                    item['red_percent'] = f"{(item['red_zone'] / item['total']) * 100:.1f}".replace(',', '.')
                    item['yellow_percent'] = f"{(item['yellow_zone'] / item['total']) * 100:.1f}".replace(',', '.')
                    item['green_percent'] = f"{(item['green_zone'] / item['total']) * 100:.1f}".replace(',', '.')
                else:
                    item['red_percent'] = "0.0"
                    item['yellow_percent'] = "0.0"
                    item['green_percent'] = "0.0"
                    
            # Преобразуем словарь в список и сортируем по имени ТУ/ДО
            stats = list(ter_admin_stats.values())
            stats.sort(key=lambda x: x['ter_admin_name'])
            
            # Для отладки
            print(f"DEBUG - One year or all years: {len(stats)} items in stats")
            
        else:
            # Если нужно показывать столбец "Год", собираем данные по каждому году отдельно
            year_stats_list = []
            
            for year in selected_years:
                # Получаем отчеты для выбранного года
                reports = Report.objects.filter(year=year, is_published=True)
                
                # Получаем отчеты школ, которые были приняты (статус 'D')
                schools_reports = SchoolReport.objects.filter(
                    report__in=reports,
                    status='D'  # Только принятые отчеты
                )
                
                # Словарь для текущего года
                year_stats = {}
                
                # Подсчитываем отчеты по зонам для каждого ТУ/ДО
                for report in schools_reports:
                    # Пропускаем отчеты без школы или с архивной школой
                    if not report.school or report.school.is_archived:
                        continue
                    
                    ter_admin_id = report.school.ter_admin_id
                    
                    # Инициализируем словарь для ТУ/ДО, если его еще нет
                    if ter_admin_id not in year_stats:
                        ter_admin = TerAdmin.objects.get(id=ter_admin_id)
                        year_stats[ter_admin_id] = {
                            'year': year.year,
                            'ter_admin_id': ter_admin_id,
                            'ter_admin_name': ter_admin.name,
                            'red_zone': 0,
                            'yellow_zone': 0,
                            'green_zone': 0,
                            'total': 0
                        }
                    
                    # Увеличиваем счетчик для соответствующей зоны
                    if report.zone == 'R':
                        year_stats[ter_admin_id]['red_zone'] += 1
                    elif report.zone == 'Y':
                        year_stats[ter_admin_id]['yellow_zone'] += 1
                    elif report.zone == 'G':
                        year_stats[ter_admin_id]['green_zone'] += 1
                    
                    # Увеличиваем общий счетчик отчетов для ТУ/ДО
                    year_stats[ter_admin_id]['total'] += 1
                
                # Рассчитываем проценты для каждого ТУ/ДО за текущий год
                for ter_admin_id in year_stats:
                    item = year_stats[ter_admin_id]
                    if item['total'] > 0:
                        item['red_percent'] = f"{(item['red_zone'] / item['total']) * 100:.1f}".replace(',', '.')
                        item['yellow_percent'] = f"{(item['yellow_zone'] / item['total']) * 100:.1f}".replace(',', '.')
                        item['green_percent'] = f"{(item['green_zone'] / item['total']) * 100:.1f}".replace(',', '.')
                    else:
                        item['red_percent'] = "0.0"
                        item['yellow_percent'] = "0.0"
                        item['green_percent'] = "0.0"
                
                # Преобразуем словарь в список и сортируем по имени ТУ/ДО
                current_year_stats = list(year_stats.values())
                current_year_stats.sort(key=lambda x: x['ter_admin_name'])
                
                # Добавляем статистику за текущий год в общий список
                year_stats_list.extend(current_year_stats)
            
            # Для отладки
            print(f"DEBUG - Multiple years: {len(year_stats_list)} total items across years")
            
            # Сохраняем несгруппированную статистику для использования в Excel
            stats_for_excel = year_stats_list
            
            # Группируем данные по ТУ/ДО для отображения в шаблоне
            grouped_stats = {}
            for item in year_stats_list:
                ter_admin_name = item['ter_admin_name']
                if ter_admin_name not in grouped_stats:
                    grouped_stats[ter_admin_name] = []
                grouped_stats[ter_admin_name].append(item)
            
            # Преобразуем сгруппированные данные в формат для шаблона
            stats_grouped = []
            for ter_admin_name in sorted(grouped_stats.keys()):
                # Сортируем элементы группы по году (по убыванию)
                items = sorted(grouped_stats[ter_admin_name], key=lambda x: x.get('year', 0), reverse=True)
                stats_grouped.append({
                    'ter_admin_name': ter_admin_name,
                    'years': items,
                    'rowspan': len(items)
                })
            
            # Используем сгруппированную статистику для отображения
            stats = stats_grouped
            
            # Для отладки
            print(f"DEBUG - After grouping: {len(stats)} ТУ/ДО groups")
    
    # Получаем статистику по разделам и кластерам
    section_stats = calculate_section_stats(selected_years, show_year_column)
    cluster_stats = calculate_cluster_stats(selected_years, show_year_column)
    
    # Для отладки
    print(f"DEBUG - section_stats: {len(section_stats) if section_stats else 0} items")
    print(f"DEBUG - cluster_stats: {len(cluster_stats) if cluster_stats else 0} items")
    
    # Подготавливаем контекст для шаблона
    context = {
        'filter': filter_context,
        'stats': stats,
        'selected_years': selected_years,
        'selected_year_ids': [str(year.id) for year in selected_years] if selected_years else [],
        'show_year_column': show_year_column  # Флаг, показывающий, нужен ли столбец с годом
    }
    
    # Добавляем статистику по разделам и кластерам
    if section_stats:
        context['section_stats'] = section_stats
    
    if cluster_stats:
        context['cluster_stats'] = cluster_stats
        
    # Генерируем статистику по индикаторам (показателям)
    if selected_years:
        # Собираем статистику по показателям для каждого раздела
        indicator_stats = []
        
        # Получаем все разделы для выбранных годов, сгруппированные по имени
        section_names = Section.objects.filter(
            report__year__in=selected_years
        ).values_list('name', 'number').distinct()
        
        # Создаем словарь для быстрого доступа
        section_dict = {name: number for name, number in section_names}
        
        # Получаем все принятые отчеты школ для выбранных годов
        all_school_reports = SchoolReport.objects.filter(
            report__year__in=selected_years,
            status='D'
        ).exclude(
            school=None
        ).exclude(
            school__is_archived=True
        ).select_related('school__ter_admin')
        
        # Для каждого раздела собираем данные по показателям
        for section_name, section_number in section_names:
            # Находим все разделы с указанным именем
            same_name_sections = Section.objects.filter(
                name=section_name,
                report__year__in=selected_years
            )
            
            # Получаем все поля (показатели) для текущего раздела
            fields = Field.objects.filter(
                sections__in=same_name_sections
            ).distinct().values('id', 'name', 'number')
            
            section_indicators = []
            
            # Для каждого поля (показателя) собираем статистику по ТУ/ДО
            for field in fields:
                field_id = field['id']
                
                # Словарь для сбора статистики по ТУ/ДО
                ter_admin_stats = {}
                
                # Получаем все ответы по этому показателю
                answers = Answer.objects.filter(
                    question_id=field_id,
                    s_report__in=all_school_reports
                ).select_related('s_report__school__ter_admin')
                
                # Создаем уникальный набор комбинаций [отчет, ТУ/ДО] для избежания дублей
                processed_reports = set()
                
                # Собираем статистику по зонам для каждого ТУ/ДО
                for answer in answers:
                    s_report = answer.s_report
                    school = s_report.school
                    
                    if not school or not school.ter_admin:
                        continue
                    
                    # Создаем уникальный ключ для комбинации отчета и ТУ/ДО
                    key = (s_report.id, school.ter_admin.id)
                    
                    # Пропускаем, если уже обработали этот отчет для этого ТУ/ДО
                    if key in processed_reports:
                        continue
                    
                    processed_reports.add(key)
                    
                    ter_admin_name = school.ter_admin.name
                    
                    # Инициализируем счетчики для ТУ/ДО, если их еще нет
                    if ter_admin_name not in ter_admin_stats:
                        ter_admin_stats[ter_admin_name] = {
                            'ter_admin_name': ter_admin_name,
                            'red_zone': 0,
                            'yellow_zone': 0,
                            'green_zone': 0,
                            'total': 0
                        }
                    
                    # Увеличиваем счетчик для соответствующей зоны
                    if answer.zone == 'R':
                        ter_admin_stats[ter_admin_name]['red_zone'] += 1
                    elif answer.zone == 'Y':
                        ter_admin_stats[ter_admin_name]['yellow_zone'] += 1
                    elif answer.zone == 'G':
                        ter_admin_stats[ter_admin_name]['green_zone'] += 1
                    
                    # Увеличиваем общий счетчик
                    ter_admin_stats[ter_admin_name]['total'] += 1
                
                # Рассчитываем проценты для каждого ТУ/ДО
                for ter_admin_name in ter_admin_stats:
                    item = ter_admin_stats[ter_admin_name]
                    if item['total'] > 0:
                        item['red_percent'] = f"{(item['red_zone'] / item['total']) * 100:.1f}".replace(',', '.')
                        item['yellow_percent'] = f"{(item['yellow_zone'] / item['total']) * 100:.1f}".replace(',', '.')
                        item['green_percent'] = f"{(item['green_zone'] / item['total']) * 100:.1f}".replace(',', '.')
                    else:
                        item['red_percent'] = "0.0"
                        item['yellow_percent'] = "0.0"
                        item['green_percent'] = "0.0"
                
                # Преобразуем в список и сортируем по имени ТУ/ДО
                ter_admin_list = list(ter_admin_stats.values())
                ter_admin_list.sort(key=lambda x: x['ter_admin_name'])
                
                # Если есть данные для этого поля, добавляем его в список
                if ter_admin_list:
                    section_indicators.append({
                        'field_id': field_id,
                        'field_name': field['name'],
                        'field_number': field['number'],
                        'ter_admin_stats': ter_admin_list
                    })
            
            # Сортируем показатели по номеру
            section_indicators.sort(key=lambda x: float(x['field_number']) if x['field_number'] and x['field_number'].replace('.', '', 1).isdigit() else float('inf'))
            
            # Если есть показатели для этого раздела, добавляем его в список
            if section_indicators:
                indicator_stats.append({
                    'section_number': section_number,
                    'section_name': section_name,
                    'indicators': section_indicators
                })
        
        # Сортируем разделы по номеру
        indicator_stats.sort(key=lambda x: float(x['section_number']) if x['section_number'] and x['section_number'].replace('.', '', 1).isdigit() else float('inf'))
        
        # Добавляем данные в контекст
        context['indicator_stats'] = indicator_stats
    
    # Обрабатываем запрос на скачивание Excel-файла
    if request.method == 'POST' and 'download' in request.POST:
        try:
            # Для выгрузки в Excel используем подходящие данные
            if show_year_column:
                # Для нескольких лет используем несгруппированный список
                if 'stats_for_excel' in locals():
                    excel_data = stats_for_excel
                else:
                    # Если stats_for_excel не определен, но stats сгруппирован
                    if stats and isinstance(stats, list) and stats and isinstance(stats[0], dict) and 'years' in stats[0]:
                        # Разгруппировываем данные
                        flat_stats = []
                        for group in stats:
                            flat_stats.extend(group.get('years', []))
                        excel_data = flat_stats
                    else:
                        # Если статистика не сгруппирована
                        excel_data = stats
            else:
                # Для одного года просто используем stats
                excel_data = stats
            
            # Убедимся, что excel_data не пустой
            if not excel_data:
                excel_data = []
                print("WARNING: Empty excel_data!")
            
            # Дополнительная проверка структуры excel_data для отладки
            print(f"DEBUG - excel_data type: {type(excel_data)}")
            if excel_data and isinstance(excel_data, list):
                print(f"DEBUG - First item in excel_data: {excel_data[0].keys() if isinstance(excel_data[0], dict) else 'Not a dict'}")
            
            # Создаем Excel-файл
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="report_distribution.xlsx"'
            
            # Генерируем Excel с распределением зон
            print(f"DEBUG - Before generate_zone_distribution_excel")
            wb = generate_zone_distribution_excel(selected_years, excel_data, show_year_column, section_stats, cluster_stats, indicator_stats)
            print(f"DEBUG - After generate_zone_distribution_excel")
            return wb
        except Exception as e:
            # Логируем ошибку
            print(f"ERROR when generating Excel: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            # Возвращаем сообщение об ошибке
            messages.error(request, f"Ошибка при формировании Excel-отчета: {str(e)}")
            # Возвращаем страницу без скачивания файла
            return render(request, 'dashboards/answers_distribution_report.html', context)

    # Возвращаем шаблон с контекстом
    return render(request, 'dashboards/answers_distribution_report.html', context)

def generate_zone_distribution_excel(years, stats, show_year_column=False, section_stats=None, cluster_stats=None, indicator_stats=None):
    """
    Генерирует Excel-файл с распределением зон по ТУ/ДО, разделам и кластерам,
    а также с детальной информацией по школам и показателям
    """
    # Отладочные сообщения для проверки входных данных
    print(f"DEBUG - Generating Excel, stats: {len(stats) if stats else 0} items")
    print(f"DEBUG - Generating Excel, show_year_column: {show_year_column}")
    print(f"DEBUG - Generating Excel, section_stats: {len(section_stats) if section_stats else 0} items")
    print(f"DEBUG - Generating Excel, cluster_stats: {len(cluster_stats) if cluster_stats else 0} items")
    
    # Проверяем и исправляем входные данные
    if not stats:
        stats = []
    
    if not section_stats:
        section_stats = []
    
    if not cluster_stats:
        cluster_stats = []
    
    # Если stats - это список словарей с ключом 'years', разгруппируем его
    if show_year_column and stats and isinstance(stats, list) and stats and isinstance(stats[0], dict) and 'years' in stats[0]:
        print("DEBUG - Stats is grouped, flattening it")
        flat_stats = []
        for group in stats:
            flat_stats.extend(group.get('years', []))
        stats = flat_stats
    
    # Создаем Excel-файл
    output = BytesIO()
    workbook = Workbook()
    
    # Переименовываем первый лист в "Визуализация"
    visualization_sheet = workbook.active
    visualization_sheet.title = "Визуализация"
    
    # Стили для ячеек
    red_fill = PatternFill(start_color='FFFF0000', end_color='FFFF0000', fill_type='solid')
    yellow_fill = PatternFill(start_color='FFFFFF00', end_color='FFFFFF00', fill_type='solid')
    green_fill = PatternFill(start_color='FF00FF00', end_color='FF00FF00', fill_type='solid')
    bold_font = Font(bold=True)
    
    # ========== ВКЛАДКА "ВИЗУАЛИЗАЦИЯ" ==========
    # Заголовок
    row_num = 1
    visualization_sheet.cell(row=row_num, column=1, value="Распределение отчетов по зонам").font = bold_font
    row_num += 2
    
    # Заголовки столбцов
    headers = ["ТУ/ДО"]
    
    # Добавляем столбец "Год" после ТУ/ДО, если нужно
    if show_year_column:
        headers.append("Год")
    
    headers.extend(["Красная зона", "Жёлтая зона", "Зелёная зона", "Всего отчетов"])
    
    for col_num, header in enumerate(headers, 1):
        cell = visualization_sheet.cell(row=row_num, column=col_num, value=header)
        cell.font = bold_font
    row_num += 1
    
    try:
        # Защитный блок для отлова ошибок при работе с данными
        if not stats:
            # Если нет данных, выводим сообщение
            visualization_sheet.cell(row=row_num, column=1, value="Нет данных для отображения")
            row_num += 1
        # Если выбрано несколько лет, группируем данные по ТУ/ДО
        elif show_year_column:
            # Проверяем структуру данных
            if not all(isinstance(item, dict) and 'ter_admin_name' in item for item in stats):
                visualization_sheet.cell(row=row_num, column=1, value="Ошибка в структуре данных")
                row_num += 1
            else:
                # Группируем данные по ter_admin_name
                ter_admin_groups = {}
                for item in stats:
                    ter_admin_name = item.get('ter_admin_name', 'Неизвестно')
                    if ter_admin_name not in ter_admin_groups:
                        ter_admin_groups[ter_admin_name] = []
                    ter_admin_groups[ter_admin_name].append(item)
                
                # Отображаем данные по группам с объединением ячеек
                for ter_admin_name in sorted(ter_admin_groups.keys()):
                    group_items = ter_admin_groups[ter_admin_name]
                    start_row = row_num
                    
                    # Сортируем элементы группы по году
                    group_items.sort(key=lambda x: x.get('year', 0), reverse=True)
                    
                    # Проходим по всем годам для текущего ТУ/ДО
                    for item in group_items:
                        col = 1
                        
                        # Название ТУ/ДО (добавляем только в первую строку группы)
                        if row_num == start_row:
                            visualization_sheet.cell(row=row_num, column=col, value=ter_admin_name)
                        col += 1
                        
                        # Год
                        visualization_sheet.cell(row=row_num, column=col, value=item.get('year', ''))
                        col += 1
                        
                        # Красная зона (прочерк, если 0)
                        red_zone_value = item.get('red_zone', 0)
                        cell_value = "-" if red_zone_value == 0 else red_zone_value
                        cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                        if red_zone_value > 0:
                            cell.fill = red_fill
                        col += 1
                        
                        # Жёлтая зона (прочерк, если 0)
                        yellow_zone_value = item.get('yellow_zone', 0)
                        cell_value = "-" if yellow_zone_value == 0 else yellow_zone_value
                        cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                        if yellow_zone_value > 0:
                            cell.fill = yellow_fill
                        col += 1
                        
                        # Зелёная зона (прочерк, если 0)
                        green_zone_value = item.get('green_zone', 0)
                        cell_value = "-" if green_zone_value == 0 else green_zone_value
                        cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                        if green_zone_value > 0:
                            cell.fill = green_fill
                        col += 1
                        
                        # Всего отчетов (прочерк, если 0)
                        total_value = item.get('total', 0)
                        cell_value = "-" if total_value == 0 else total_value
                        visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                        
                        row_num += 1
                    
                    # Объединяем ячейки с названием ТУ/ДО, если группа содержит более одной записи
                    if len(group_items) > 1:
                        try:
                            visualization_sheet.merge_cells(start_row=start_row, start_column=1, end_row=row_num-1, end_column=1)
                        except Exception as e:
                            print(f"DEBUG - Error merging cells: {str(e)}")
        else:
            # Если выбран один год, используем исходную логику
            # Сортируем статистику по имени ТУ/ДО
            sorted_stats = sorted(stats, key=lambda x: x.get('ter_admin_name', ''))
            for item in sorted_stats:
                col = 1
                
                # Название ТУ/ДО
                visualization_sheet.cell(row=row_num, column=col, value=item.get('ter_admin_name', 'Неизвестно'))
                col += 1
                
                # Красная зона (прочерк, если 0)
                red_zone_value = item.get('red_zone', 0)
                cell_value = "-" if red_zone_value == 0 else red_zone_value
                cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                if red_zone_value > 0:
                    cell.fill = red_fill
                col += 1
                
                # Жёлтая зона (прочерк, если 0)
                yellow_zone_value = item.get('yellow_zone', 0)
                cell_value = "-" if yellow_zone_value == 0 else yellow_zone_value
                cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                if yellow_zone_value > 0:
                    cell.fill = yellow_fill
                col += 1
                
                # Зелёная зона (прочерк, если 0)
                green_zone_value = item.get('green_zone', 0)
                cell_value = "-" if green_zone_value == 0 else green_zone_value
                cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                if green_zone_value > 0:
                    cell.fill = green_fill
                col += 1
                
                # Всего отчетов (прочерк, если 0)
                total_value = item.get('total', 0)
                cell_value = "-" if total_value == 0 else total_value
                visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                
                row_num += 1
    except Exception as e:
        # В случае ошибки выводим сообщение об ошибке в Excel
        print(f"DEBUG - Error processing stats data: {str(e)}")
        import traceback
        print(traceback.format_exc())
        visualization_sheet.cell(row=row_num, column=1, value=f"Ошибка обработки данных: {str(e)}")
        row_num += 1
    
    # Автоподбор ширины столбцов для вкладки "Визуализация"
    for column in visualization_sheet.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        visualization_sheet.column_dimensions[column_letter].width = adjusted_width
    
    # ========== ДОБАВЛЯЕМ ТАБЛИЦУ "РАСПРЕДЕЛЕНИЕ ОТЧЕТОВ ПО РАЗДЕЛАМ" ==========
    if section_stats:
        row_num += 2
        visualization_sheet.cell(row=row_num, column=1, value="Распределение отчетов по разделам").font = bold_font
        row_num += 2
        
        # Заголовки столбцов
        headers = ["Раздел"]
        
        # Добавляем столбец "Год" после Раздела, если нужно
        if show_year_column:
            headers.append("Год")
        
        headers.extend(["Красная зона", "Жёлтая зона", "Зелёная зона", "Всего отчетов"])
        
        for col_num, header in enumerate(headers, 1):
            cell = visualization_sheet.cell(row=row_num, column=col_num, value=header)
            cell.font = bold_font
        row_num += 1
        
        # Если выбрано несколько лет и данные сгруппированы
        if show_year_column and isinstance(section_stats[0], dict) and 'years' in section_stats[0]:
            # Группируем данные по названию раздела
            for section_data in section_stats:
                section_name = section_data['section_name']
                start_row = row_num
                
                # Сортируем годы
                years_data = section_data['years']
                years_data.sort(key=lambda x: x.get('year', 0))
                
                # Проходим по всем годам для текущего раздела
                for item in years_data:
                    col = 1
                    
                    # Название раздела (добавляем только в первую строку группы)
                    if row_num == start_row:
                        visualization_sheet.cell(row=row_num, column=col, value=section_name)
                    col += 1
                    
                    # Год
                    visualization_sheet.cell(row=row_num, column=col, value=item.get('year', ''))
                    col += 1
                    
                    # Красная зона (прочерк, если 0)
                    red_zone_value = item['red_zone']
                    cell_value = "-" if red_zone_value == 0 else red_zone_value
                    cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                    if red_zone_value > 0:
                        cell.fill = red_fill
                    col += 1
                    
                    # Жёлтая зона (прочерк, если 0)
                    yellow_zone_value = item['yellow_zone']
                    cell_value = "-" if yellow_zone_value == 0 else yellow_zone_value
                    cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                    if yellow_zone_value > 0:
                        cell.fill = yellow_fill
                    col += 1
                    
                    # Зелёная зона (прочерк, если 0)
                    green_zone_value = item['green_zone']
                    cell_value = "-" if green_zone_value == 0 else green_zone_value
                    cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                    if green_zone_value > 0:
                        cell.fill = green_fill
                    col += 1
                    
                    # Всего отчетов (прочерк, если 0)
                    total_value = item['total']
                    cell_value = "-" if total_value == 0 else total_value
                    visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                    
                    row_num += 1
                
                # Объединяем ячейки с названием раздела, если группа содержит более одной записи
                if len(years_data) > 1:
                    visualization_sheet.merge_cells(start_row=start_row, start_column=1, end_row=row_num-1, end_column=1)
        else:
            # Если один год или данные не сгруппированы
            for item in section_stats:
                col = 1
                
                # Название раздела
                visualization_sheet.cell(row=row_num, column=col, value=item['section_name'])
                col += 1
                
                # Год (если нужно)
                if show_year_column:
                    visualization_sheet.cell(row=row_num, column=col, value=item.get('year', ''))
                    col += 1
                
                # Красная зона (прочерк, если 0)
                red_zone_value = item['red_zone']
                cell_value = "-" if red_zone_value == 0 else red_zone_value
                cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                if red_zone_value > 0:
                    cell.fill = red_fill
                col += 1
                
                # Жёлтая зона (прочерк, если 0)
                yellow_zone_value = item['yellow_zone']
                cell_value = "-" if yellow_zone_value == 0 else yellow_zone_value
                cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                if yellow_zone_value > 0:
                    cell.fill = yellow_fill
                col += 1
                
                # Зелёная зона (прочерк, если 0)
                green_zone_value = item['green_zone']
                cell_value = "-" if green_zone_value == 0 else green_zone_value
                cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                if green_zone_value > 0:
                    cell.fill = green_fill
                col += 1
                
                # Всего отчетов (прочерк, если 0)
                total_value = item['total']
                cell_value = "-" if total_value == 0 else total_value
                visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                
                row_num += 1
        

    # ========== ДОБАВЛЯЕМ ТАБЛИЦУ "РАСПРЕДЕЛЕНИЕ ОТЧЕТОВ ПО КЛАСТЕРАМ" ==========
    if cluster_stats:
        row_num += 2
        visualization_sheet.cell(row=row_num, column=1, value="Распределение отчетов по кластерам").font = bold_font
        row_num += 2
        
        # Заголовки столбцов
        headers = ["Кластер"]
        
        # Добавляем столбец "Год" после Кластера, если нужно
        if show_year_column:
            headers.append("Год")
        
        headers.extend(["Красная зона", "Жёлтая зона", "Зелёная зона", "Всего отчетов"])
        
        for col_num, header in enumerate(headers, 1):
            cell = visualization_sheet.cell(row=row_num, column=col_num, value=header)
            cell.font = bold_font
        row_num += 1
        
        # Если выбрано несколько лет и данные сгруппированы
        if show_year_column and isinstance(cluster_stats[0], dict) and 'years' in cluster_stats[0]:
            # Группируем данные по названию кластера
            for cluster_data in cluster_stats:
                cluster_name = cluster_data['cluster_name']
                start_row = row_num
                
                # Сортируем годы
                years_data = cluster_data['years']
                years_data.sort(key=lambda x: x.get('year', 0))
                
                # Проходим по всем годам для текущего кластера
                for item in years_data:
                    col = 1
                    
                    # Название кластера (добавляем только в первую строку группы)
                    if row_num == start_row:
                        visualization_sheet.cell(row=row_num, column=col, value=cluster_name)
                    col += 1
                    
                    # Год
                    visualization_sheet.cell(row=row_num, column=col, value=item.get('year', ''))
                    col += 1
                    
                    # Красная зона (прочерк, если 0)
                    red_zone_value = item['red_zone']
                    cell_value = "-" if red_zone_value == 0 else red_zone_value
                    cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                    if red_zone_value > 0:
                        cell.fill = red_fill
                    col += 1
                    
                    # Жёлтая зона (прочерк, если 0)
                    yellow_zone_value = item['yellow_zone']
                    cell_value = "-" if yellow_zone_value == 0 else yellow_zone_value
                    cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                    if yellow_zone_value > 0:
                        cell.fill = yellow_fill
                    col += 1
                    
                    # Зелёная зона (прочерк, если 0)
                    green_zone_value = item['green_zone']
                    cell_value = "-" if green_zone_value == 0 else green_zone_value
                    cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                    if green_zone_value > 0:
                        cell.fill = green_fill
                    col += 1
                    
                    # Всего отчетов (прочерк, если 0)
                    total_value = item['total']
                    cell_value = "-" if total_value == 0 else total_value
                    visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                    
                    row_num += 1
                
                # Объединяем ячейки с названием кластера, если группа содержит более одной записи
                if len(years_data) > 1:
                    visualization_sheet.merge_cells(start_row=start_row, start_column=1, end_row=row_num-1, end_column=1)
        else:
            # Если один год или данные не сгруппированы
            for item in cluster_stats:
                col = 1
                
                # Название кластера
                visualization_sheet.cell(row=row_num, column=col, value=item['cluster_name'])
                col += 1
                
                # Год (если нужно)
                if show_year_column:
                    visualization_sheet.cell(row=row_num, column=col, value=item.get('year', ''))
                    col += 1
                
                # Красная зона (прочерк, если 0)
                red_zone_value = item['red_zone']
                cell_value = "-" if red_zone_value == 0 else red_zone_value
                cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                if red_zone_value > 0:
                    cell.fill = red_fill
                col += 1
                
                # Жёлтая зона (прочерк, если 0)
                yellow_zone_value = item['yellow_zone']
                cell_value = "-" if yellow_zone_value == 0 else yellow_zone_value
                cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                if yellow_zone_value > 0:
                    cell.fill = yellow_fill
                col += 1
                
                # Зелёная зона (прочерк, если 0)
                green_zone_value = item['green_zone']
                cell_value = "-" if green_zone_value == 0 else green_zone_value
                cell = visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                if green_zone_value > 0:
                    cell.fill = green_fill
                col += 1
                
                # Всего отчетов (прочерк, если 0)
                total_value = item['total']
                cell_value = "-" if total_value == 0 else total_value
                visualization_sheet.cell(row=row_num, column=col, value=cell_value)
                
                row_num += 1
    
    # Обновляем ширину столбцов после добавления новых таблиц
    for column in visualization_sheet.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        visualization_sheet.column_dimensions[column_letter].width = adjusted_width
    
    # ========== ВКЛАДКА "ОБЩИЙ СВОД" ==========
    # Создаем лист для общего свода
    general_sheet = workbook.create_sheet(title="Общий свод")
    
    # Получаем все отчеты школ для выбранных годов
    all_school_reports = SchoolReport.objects.filter(
        report__year__in=years,
        status='D'
    ).exclude(
        school=None
    ).exclude(
        school__is_archived=True
    ).select_related(
        'school__ter_admin',
        'school__closter',
        'report__year'
    ).prefetch_related(
        'sections',
        'answers'
    )
    
    # Заголовок
    row_num = 1
    general_sheet.cell(row=row_num, column=1, value="Общий свод по школам").font = bold_font
    row_num += 2
    
    # Получаем все разделы для выбранных годов для "Общего свода"
    sections = Section.objects.filter(
        report__year__in=years
    ).distinct('number').order_by('number')
    
    # Заголовки столбцов общего свода
    headers = ["Школа", "ТУ/ДО", "Уровень образования", "Кластер", "Итого баллов"]
    
    # Добавляем столбцы с разделами
    section_headers = [f"Раздел {s.number}" for s in sections]
    headers.extend(section_headers)
    
    for col_num, header in enumerate(headers, 1):
        cell = general_sheet.cell(row=row_num, column=col_num, value=header)
        cell.font = bold_font
    row_num += 1
    
    # Словарь для хранения уровней образования
    ed_levels = {
        'A': "1 — 11 классы",
        'M': "1 — 9 классы",
        'S': "1 — 4 классы",
        'MG': "5 — 11 классы",
        'G': "10 — 11 классы",
    }
    
    # Словарь для группировки отчетов по школам
    school_data = {}
    
    # Группируем отчеты по школам
    for s_report in all_school_reports:
        school = s_report.school
        school_id = school.id
        year = s_report.report.year
        
        if (school_id, year.id) not in school_data:
            school_data[(school_id, year.id)] = {
                'school_name': school.name,
                'ter_admin_name': school.ter_admin.name if school.ter_admin else "-",
                'ed_level': ed_levels.get(school.ed_level, "Н/Д"),
                'closter_name': school.closter.name if school.closter else "-",
                'total_points': 0,  # Инициализируем 0, посчитаем сумму позже
                'zone': s_report.zone,  # Сохраняем зону отчета
                'sections': {},
                'year': year.year
            }
        
        # Добавляем данные по секциям
        for section in s_report.sections.all():
            section_number = section.section.number
            if section_number not in school_data[(school_id, year.id)]['sections']:
                school_data[(school_id, year.id)]['sections'][section_number] = section.points
                # Добавляем баллы секции к общей сумме
                school_data[(school_id, year.id)]['total_points'] += section.points
    
    # Сортируем данные школ по ТУ/ДО и имени школы
    sorted_school_data = sorted(
        school_data.values(),
        key=lambda x: (x['ter_admin_name'], x['school_name'], x.get('year', 0))
    )
    
    # Заполняем данные по школам
    for data in sorted_school_data:
        col = 1
        
        # Название школы
        general_sheet.cell(row=row_num, column=col, value=data['school_name'])
        col += 1
        
        # ТУ/ДО
        general_sheet.cell(row=row_num, column=col, value=data['ter_admin_name'])
        col += 1
        
        # Уровень образования
        general_sheet.cell(row=row_num, column=col, value=data['ed_level'])
        col += 1
        
        # Кластер
        general_sheet.cell(row=row_num, column=col, value=data['closter_name'])
        col += 1
        
        # Итого баллов
        cell = general_sheet.cell(row=row_num, column=col, value=data['total_points'])
        # Устанавливаем цвет ячейки в зависимости от зоны
        if data.get('zone') == 'R':
            cell.fill = red_fill
        elif data.get('zone') == 'Y':
            cell.fill = yellow_fill
        elif data.get('zone') == 'G':
            cell.fill = green_fill
        col += 1
        
        # Баллы по разделам
        for section in sections:
            section_points = data['sections'].get(section.number, "-")
            general_sheet.cell(row=row_num, column=col, value=section_points)
            col += 1
        
        row_num += 1
    
    # Автоподбор ширины столбцов для вкладки "Общий свод"
    for column in general_sheet.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        general_sheet.column_dimensions[column_letter].width = adjusted_width
    
    # ========== ВКЛАДКИ ДЛЯ КАЖДОГО РАЗДЕЛА ==========
    # Получаем все разделы для выбранных годов
    all_sections = Section.objects.filter(
        report__year__in=years
    ).values('name', 'number').distinct('number').order_by('number')
    
    # Словарь для хранения уровней образования
    ed_levels = {
        'A': "1 — 11 классы",
        'M': "1 — 9 классы",
        'S': "1 — 4 классы",
        'MG': "5 — 11 классы",
        'G': "10 — 11 классы",
    }
    
    # Получаем все отчеты школ для выбранных годов
    all_school_reports = SchoolReport.objects.filter(
        report__year__in=years,
        status='D'
    ).exclude(
        school=None
    ).exclude(
        school__is_archived=True
    ).select_related(
        'school__ter_admin',
        'school__closter',
        'report__year'
    ).prefetch_related(
        'sections',
        'answers'
    )
    
    # Создаем вкладку для каждого раздела
    for section in all_sections:
        section_name = section['name']
        section_number = section['number']
        
        # Создаем имя листа без недопустимых символов (макс. 31 символ)
        safe_sheet_name = f"Раздел {section_number}"
        if len(safe_sheet_name) > 31:
            safe_sheet_name = safe_sheet_name[:28] + "..."
        
        section_sheet = workbook.create_sheet(title=safe_sheet_name)
        
        # Заголовок
        row_num = 1
        section_sheet.cell(row=row_num, column=1, value=f"Раздел {section_number}: {section_name}").font = bold_font
        row_num += 2
        
        # Получаем поля (показатели) для текущего раздела
        fields = Field.objects.filter(
            sections__number=section_number,
            sections__report__year__in=years
        ).distinct().order_by('number')
        
        # Заголовки столбцов: базовые + показатели
        headers = ["Школа", "ТУ/ДО", "Уровень образования", "Кластер"]
        field_headers = [f"{field.number}. {field.name}" for field in fields]
        headers.extend(field_headers)
        
        for col_num, header in enumerate(headers, 1):
            cell = section_sheet.cell(row=row_num, column=col_num, value=header)
            cell.font = bold_font
        row_num += 1
        
        # Словарь для хранения данных по школам
        school_data = {}
        
        # Собираем ответы для текущего раздела
        for s_report in all_school_reports:
            school = s_report.school
            
            if not school:
                continue
            
            # Пропускаем, если нет секции для этого раздела
            report_sections = s_report.sections.filter(section__number=section_number)
            if not report_sections.exists():
                continue
            
            school_id = school.id
            
            if school_id not in school_data:
                school_data[school_id] = {
                    'school_name': school.name,
                    'ter_admin_name': school.ter_admin.name if school.ter_admin else "-",
                    'ed_level': ed_levels.get(school.ed_level, "Н/Д"),
                    'closter_name': school.closter.name if school.closter else "-",
                    'field_data': {}
                }
            
            # Собираем ответы на показатели этого раздела
            for field in fields:
                field_id = field.id
                
                # Ищем ответ для этого показателя
                answer = Answer.objects.filter(
                    question_id=field_id, 
                    s_report=s_report
                ).first()
                
                if answer:
                    field_data = {
                        'points': answer.points,
                        'zone': answer.zone
                    }
                    
                    # Если уже есть данные по этому полю, обновляем их только если ответ новее
                    if field_id in school_data[school_id]['field_data']:
                        if s_report.report.year.year > school_data[school_id]['field_data'][field_id].get('year', 0):
                            school_data[school_id]['field_data'][field_id] = field_data
                            school_data[school_id]['field_data'][field_id]['year'] = s_report.report.year.year
                    else:
                        school_data[school_id]['field_data'][field_id] = field_data
                        school_data[school_id]['field_data'][field_id]['year'] = s_report.report.year.year
        
        # Сортируем данные школ по ТУ/ДО и имени школы
        sorted_school_data = sorted(
            school_data.values(),
            key=lambda x: (x['ter_admin_name'], x['school_name'])
        )
        
        # Заполняем данные по школам
        for data in sorted_school_data:
            col = 1
            
            # Название школы
            section_sheet.cell(row=row_num, column=col, value=data['school_name'])
            col += 1
            
            # ТУ/ДО
            section_sheet.cell(row=row_num, column=col, value=data['ter_admin_name'])
            col += 1
            
            # Уровень образования
            section_sheet.cell(row=row_num, column=col, value=data['ed_level'])
            col += 1
            
            # Кластер
            section_sheet.cell(row=row_num, column=col, value=data['closter_name'])
            col += 1
            
            # Данные по показателям
            for field in fields:
                field_id = field.id
                field_data = data['field_data'].get(field_id, {})
                
                if field_data:
                    points = field_data.get('points', "-")
                    zone = field_data.get('zone', '')
                    
                    cell = section_sheet.cell(row=row_num, column=col, value=points)
                    
                    # Устанавливаем цвет ячейки в зависимости от зоны
                    if zone == 'R':
                        cell.fill = red_fill
                    elif zone == 'Y':
                        cell.fill = yellow_fill
                    elif zone == 'G':
                        cell.fill = green_fill
                else:
                    section_sheet.cell(row=row_num, column=col, value="-")
                
                col += 1
            
            row_num += 1
        
        # Автоподбор ширины столбцов для вкладки раздела
        for column in section_sheet.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            section_sheet.column_dimensions[column_letter].width = adjusted_width
    
    # Сохраняем файл
    workbook.save(output)
    output.seek(0)
    
    # Генерируем HTTP-ответ
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    years_str = "-".join([str(year.year) for year in years])
    response['Content-Disposition'] = f'attachment; filename="zone_distribution_{years_str}.xlsx"'
    
    return response

# Вспомогательные функции для расчета статистики (добавить в конец файла)
def calculate_section_stats(selected_years, show_year_column=False):
    """
    Рассчитывает статистику по разделам для выбранных годов.
    """
    section_stats = []
    section_stats_by_year = []
    
    # Получаем все разделы для выбранных годов, сгруппированные по имени
    section_names = Section.objects.filter(
        report__year__in=selected_years
    ).values_list('name', flat=True).distinct()
    
    for section_name in section_names:
        if not show_year_column:
            # Находим все разделы с указанным именем
            same_name_sections = Section.objects.filter(
                name=section_name,
                report__year__in=selected_years
            ).values_list('id', flat=True)
            
            # Агрегированная статистика по разделам для всех годов
            school_reports = SchoolReport.objects.filter(
                report__year__in=selected_years, 
                report__is_published=True,
                status='D'
            ).select_related('school')
            
            # Подсчитываем количество отчетов в каждой зоне для текущего раздела
            red_zone = 0
            yellow_zone = 0
            green_zone = 0
            total = 0
            
            # Для каждого отчета школы определяем зону данного раздела
            for sr in school_reports:
                # Пропускаем отчеты без школы или с архивной школой
                if not sr.school or sr.school.is_archived:
                    continue
                
                # Находим секцию отчета, соответствующую любому из разделов с тем же именем
                report_sections = sr.sections.filter(section__id__in=same_name_sections)
                
                # Проверяем только одну секцию для каждого отчета (первую найденную)
                if report_sections.exists():
                    report_section = report_sections.first()
                    if report_section.zone == 'R':
                        red_zone += 1
                    elif report_section.zone == 'Y':
                        yellow_zone += 1
                    elif report_section.zone == 'G':
                        green_zone += 1
                    total += 1
            
            if total > 0:
                section_stats.append({
                    'section_name': section_name,
                    'red_zone': red_zone,
                    'yellow_zone': yellow_zone,
                    'green_zone': green_zone,
                    'total': total,
                    'red_percent': f"{(red_zone / total) * 100:.1f}".replace(',', '.'),
                    'yellow_percent': f"{(yellow_zone / total) * 100:.1f}".replace(',', '.'),
                    'green_percent': f"{(green_zone / total) * 100:.1f}".replace(',', '.')
                })
        else:
            # Статистика по разделам с разбивкой по годам
            section_years_stats = []
            
            for year in selected_years:
                # Находим все разделы с тем же именем для текущего года
                same_name_sections = Section.objects.filter(
                    name=section_name,
                    report__year=year
                ).values_list('id', flat=True)
                
                # Если нет разделов с таким именем для этого года, пропускаем
                if not same_name_sections.exists():
                    continue
                
                school_reports = SchoolReport.objects.filter(
                    report__year=year, 
                    report__is_published=True,
                    status='D'
                ).select_related('school')
                
                # Подсчитываем количество отчетов в каждой зоне для текущего раздела и года
                red_zone = 0
                yellow_zone = 0
                green_zone = 0
                total = 0
                
                # Для каждого отчета школы определяем зону данного раздела
                for sr in school_reports:
                    # Пропускаем отчеты без школы или с архивной школой
                    if not sr.school or sr.school.is_archived:
                        continue
                    
                    # Находим секцию отчета, соответствующую любому из разделов с тем же именем
                    report_sections = sr.sections.filter(section__id__in=same_name_sections)
                    
                    # Проверяем только одну секцию для каждого отчета (первую найденную)
                    if report_sections.exists():
                        report_section = report_sections.first()
                        if report_section.zone == 'R':
                            red_zone += 1
                        elif report_section.zone == 'Y':
                            yellow_zone += 1
                        elif report_section.zone == 'G':
                            green_zone += 1
                        total += 1
                
                if total > 0:
                    # Данные по годам добавляем в отдельную структуру
                    section_years_stats.append({
                        'year': year.year,
                        'red_zone': red_zone,
                        'yellow_zone': yellow_zone,
                        'green_zone': green_zone,
                        'total': total,
                        'red_percent': f"{(red_zone / total) * 100:.1f}".replace(',', '.'),
                        'yellow_percent': f"{(yellow_zone / total) * 100:.1f}".replace(',', '.'),
                        'green_percent': f"{(green_zone / total) * 100:.1f}".replace(',', '.')
                    })
            
            if section_years_stats:
                # Группируем данные по разделам
                section_stats_by_year.append({
                    'section_name': section_name,
                    'years': section_years_stats,
                    'rowspan': len(section_years_stats)
                })
    
    # Выбираем правильную структуру данных в зависимости от режима отображения
    if show_year_column:
        return section_stats_by_year
    return section_stats

def calculate_cluster_stats(selected_years, show_year_column=False):
    """
    Рассчитывает статистику по кластерам для выбранных годов.
    """
    cluster_stats = []
    
    # Получаем все кластеры
    clusters = SchoolCloster.objects.all()
    
    for cluster in clusters:
        if not show_year_column:
            # Агрегированная статистика по кластерам для всех годов
            school_reports = SchoolReport.objects.filter(
                report__year__in=selected_years, 
                report__is_published=True,
                status='D',
                school__closter=cluster
            ).select_related('school')
            
            # Подсчитываем количество отчетов в каждой зоне для текущего кластера
            red_zone = 0
            yellow_zone = 0
            green_zone = 0
            total = 0
            
            # Для каждого отчета школы определяем общую зону отчета
            for sr in school_reports:
                # Пропускаем отчеты без школы или с архивной школой
                if not sr.school or sr.school.is_archived:
                    continue
                
                if sr.zone == 'R':
                    red_zone += 1
                elif sr.zone == 'Y':
                    yellow_zone += 1
                elif sr.zone == 'G':
                    green_zone += 1
                total += 1
            
            if total > 0:
                cluster_stats.append({
                    'cluster_name': cluster.name,
                    'red_zone': red_zone,
                    'yellow_zone': yellow_zone,
                    'green_zone': green_zone,
                    'total': total,
                    'red_percent': f"{(red_zone / total) * 100:.1f}".replace(',', '.'),
                    'yellow_percent': f"{(yellow_zone / total) * 100:.1f}".replace(',', '.'),
                    'green_percent': f"{(green_zone / total) * 100:.1f}".replace(',', '.')
                })
        else:
            # Статистика по кластерам с разбивкой по годам
            cluster_years_stats = []
            
            for year in selected_years:
                school_reports = SchoolReport.objects.filter(
                    report__year=year, 
                    report__is_published=True,
                    status='D',
                    school__closter=cluster
                ).select_related('school')
                
                # Подсчитываем количество отчетов в каждой зоне для текущего кластера и года
                red_zone = 0
                yellow_zone = 0
                green_zone = 0
                total = 0
                
                # Для каждого отчета школы определяем общую зону отчета
                for sr in school_reports:
                    # Пропускаем отчеты без школы или с архивной школой
                    if not sr.school or sr.school.is_archived:
                        continue
                    
                    if sr.zone == 'R':
                        red_zone += 1
                    elif sr.zone == 'Y':
                        yellow_zone += 1
                    elif sr.zone == 'G':
                        green_zone += 1
                    total += 1
                
                if total > 0:
                    cluster_years_stats.append({
                        'year': year.year,
                        'red_zone': red_zone,
                        'yellow_zone': yellow_zone,
                        'green_zone': green_zone,
                        'total': total,
                        'red_percent': f"{(red_zone / total) * 100:.1f}".replace(',', '.'),
                        'yellow_percent': f"{(yellow_zone / total) * 100:.1f}".replace(',', '.'),
                        'green_percent': f"{(green_zone / total) * 100:.1f}".replace(',', '.')
                    })
            
            if cluster_years_stats:
                # Группируем данные по кластерам
                cluster_stats.append({
                    'cluster_name': cluster.name,
                    'years': cluster_years_stats,
                    'rowspan': len(cluster_years_stats)
                })
    
    return cluster_stats
