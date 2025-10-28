import io
import xlsxwriter
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.core.paginator import Paginator

from reports.models import Answer, Field, Report,SchoolReport, SectionSreport, Year
from reports.utils import count_section_points
from users.models import Group, Notification, MainPageArticle
from schools.models import School, SchoolCloster, TerAdmin
from common.utils import get_cache_key
from reports.report_handlers import (
    handle_ajax_request, 
    get_report_context, 
    handle_send_report, 
    handle_file_upload
)

@login_required
def index(request):
    user = request.user
    principal_group = Group.objects.get(name='Представитель школы')
    if user.groups.filter(id=principal_group.id).count() == 1 and user.school != None:
        return HttpResponseRedirect(reverse('start'))
    teradmin_group = Group.objects.get(name='Представитель ТУ/ДО')
    if user.groups.filter(id=teradmin_group.id).count() == 1 and user.ter_admin != None:
        return HttpResponseRedirect(reverse('start'))
    mo_group = Group.objects.get(name='Представитель МинОбр')
    if user.groups.filter(id=mo_group.id).count() == 1:
        return HttpResponseRedirect(reverse('start'))
    iro_group = Group.objects.get(name='Представитель ИРО')
    if user.is_superuser or user.groups.filter(id=iro_group.id).count() == 1:
        return HttpResponseRedirect(reverse('ter_admins_reports'))
    return HttpResponseRedirect(reverse('undefined_user'))


@login_required
def start(request):
    user = request.user
    user_id = None
    principal_group = Group.objects.get(name='Представитель школы')
    if user.groups.filter(id=principal_group.id).count() == 1:
        school = user.school
    else: school = None
    teradmin_group = Group.objects.get(name='Представитель ТУ/ДО')
    if user.groups.filter(id=teradmin_group.id).count() == 1:
        user_id = user.id
    return render(request, "reports/index.html", {
        'school': school,
        'user_id': user_id,
        'messages': MainPageArticle.objects.all()
    })


@login_required
def reports(request, school_id):
    school = get_object_or_404(School, id=school_id)
    
    # Get all published reports for the school's cluster and education level
    all_reports = Report.objects.filter(closter=school.closter, ed_level=school.ed_level, is_published=True).order_by('year').distinct()
    
    # Filter reports based on year status - only show reports for years that are in 'filling' status or later
    filtered_reports = []
    for report in all_reports:
        # Check year status - only show if status is 'filling' or 'completed'
        if report.year.status in ['filling', 'completed']:
            filtered_reports.append(report)
    
    s_reports = SchoolReport.objects.filter(school=school)
    reports_list = []
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    for notification in notifications:
        notification.is_read = True
        notification.save()
        
    for report in filtered_reports:
        s_report = s_reports.filter(report=report).first()
        reports_list.append([report, s_report])

    return render(request, "reports/reports.html", {
        'school': school,
        'reports': reports_list,
        'notifications': notifications
    })

    
@login_required
@csrf_exempt
def report(request, report_id, school_id):
    """
    Рефакторенная версия функции report
    """
    report = get_object_or_404(Report, id=report_id)
    school = get_object_or_404(School, id=school_id)

    # Check year status
    if report.year.status == 'forming':
        return render(request, "reports/report_not_available.html", {
            'school': school,
            'report': report,
            'message': "Отчет в стадии формирования и пока недоступен для заполнения."
        })
    
    is_readonly = report.year.status == 'completed'
    current_section = request.GET.get('current_section', '')
    message = None

    # Get or create school report
    s_report, is_new_report = SchoolReport.objects.get_or_create(
        report=report, school=school
    )
    
    # Create answers for all questions
    sections = report.sections.all()
    for question in Field.objects.filter(sections__in=sections):
        try:
            Answer.objects.get_or_create(
                s_report=s_report,
                question=question,
            )
        except:
            answers = Answer.objects.filter(question=question, s_report=s_report)
            if len(answers) > 1:
                first_answer = answers.first()
                answers.exclude(id=first_answer.id).delete()

    if request.method == 'POST' and not is_readonly:
        if 'send-report' in request.POST:
            if s_report.status == 'C':
                message = handle_send_report(s_report, 'A')
        elif request.FILES.get("file") is not None:
            id = request.POST.dict()['id']
            question = Field.objects.get(id=id)
            return handle_file_upload(request, question, s_report)
        else:
            # Блокируем все изменения через AJAX, если год завершен
            if is_readonly:
                return JsonResponse({"error": "Редактирование недоступно. Год закрыт."}, status=403)
            return handle_ajax_request(request, s_report, user_type='school')

    context = get_report_context(request, s_report, current_section, message)
    return render(request, "reports/report.html", context)


@login_required
@csrf_exempt
def mo_reports(request):
    schools = School.objects.filter(is_archived=False)
    ter_admins = TerAdmin.objects.all()
    closters = SchoolCloster.objects.filter(schools__in=schools).distinct()
    
    # Оптимизируем запрос для отчетов, подгружая связанные данные
    s_reports = SchoolReport.objects.filter(
        school__in=schools, 
        report__is_published=True
    ).select_related(
        'school',
        'report',
        'report__year',
        'report__closter',
        'school__ter_admin'
    ).prefetch_related(
        'answers',
        'report__sections',
        'report__sections__fields'
    ).order_by('-report__year__year', 'school__name')  # Сортировка сначала по году, затем по школе

    # Список годов для фильтрации и текущий год
    years = Year.objects.all().order_by('-year')
    current_year_obj = Year.objects.filter(is_current=True).first()

    filter = None
    # Reset filter if requested or if it's a GET request without pagination
    if 'reset' in request.GET or (request.method == 'GET' and 'page' not in request.GET):
        if 'mo_reports_filter' in request.session:
            del request.session['mo_reports_filter']
        if 'reset' in request.GET:
            return HttpResponseRedirect(reverse('mo_reports'))
    
    # Если не задан фильтр (ни в POST, ни в сессии) — показываем отчёты текущего года
    if 'filter' not in request.POST and 'mo_reports_filter' not in request.session and current_year_obj:
        s_reports = s_reports.filter(report__year=current_year_obj)

    # Store filter parameters in session when POST request
    if 'filter' in request.POST:
        filter_params = {}
        if len(request.POST.getlist('ter_admins')) != 0:
            schools = schools.filter(ter_admin__in=request.POST.getlist('ter_admins'))
            s_reports = s_reports.filter(school__in=schools)
            filter_params['ter_admins'] = request.POST.getlist('ter_admins')
        if len(request.POST.getlist('closters')) != 0:
            schools = schools.filter(closter__in=request.POST.getlist('closters'))
            s_reports = s_reports.filter(school__in=schools)
            filter_params['closters'] = request.POST.getlist('closters')
        if len(request.POST.getlist('ed_levels')) != 0:
            schools = schools.filter(ed_level__in=request.POST.getlist('ed_levels'))
            s_reports = s_reports.filter(school__in=schools)
            filter_params['ed_levels'] = request.POST.getlist('ed_levels')
        if len(request.POST.getlist('status')) != 0:
            s_reports = s_reports.filter(status__in=request.POST.getlist('status'))
            filter_params['status'] = request.POST.getlist('status')
        if len(request.POST.getlist('years')) != 0:
            s_reports = s_reports.filter(report__year__in=request.POST.getlist('years'))
            filter_params['years'] = request.POST.getlist('years')
        
        filter = filter_params
        request.session['mo_reports_filter'] = filter_params
    # Use filter from session only for GET requests with pagination
    elif request.method == 'GET' and 'page' in request.GET and 'mo_reports_filter' in request.session:
        filter_params = request.session['mo_reports_filter']
        filter = filter_params
        
        if 'ter_admins' in filter_params and filter_params['ter_admins']:
            schools = schools.filter(ter_admin__in=filter_params['ter_admins'])
            s_reports = s_reports.filter(school__in=schools)
        if 'closters' in filter_params and filter_params['closters']:
            schools = schools.filter(closter__in=filter_params['closters'])
            s_reports = s_reports.filter(school__in=schools)
        if 'ed_levels' in filter_params and filter_params['ed_levels']:
            schools = schools.filter(ed_level__in=filter_params['ed_levels'])
            s_reports = s_reports.filter(school__in=schools)
        if 'status' in filter_params and filter_params['status']:
            s_reports = s_reports.filter(status__in=filter_params['status'])
        if 'years' in filter_params and filter_params['years']:
            s_reports = s_reports.filter(report__year__in=filter_params['years'])
    
    if 'send-reports' in request.POST:
        s_reports.filter(status='B').update(status='D')
        return HttpResponseRedirect(reverse('mo_reports'))
    
    # Обработка запроса на экспорт данных о заполнении
    if 'export_data' in request.POST:
        # Получаем все отчеты, удовлетворяющие фильтрам (без пагинации)
        # т.к. мы хотим экспортировать все отчеты, соответствующие фильтрам
        return export_reports_to_excel(s_reports, 'mo_reports_completion.xlsx')
    
    # Pagination
    paginator = Paginator(s_reports, 20)  # 20 reports per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
        
    return render(request, "reports/mo_reports.html", {
        'reports': page_obj,
        'ter_admins': ter_admins,
        'closters': closters,
        'ed_levels': School.SCHOOL_LEVELS,
        'filter': filter,
        'paginator': paginator,
        'page_obj': page_obj,
        'years': years,
        'current_year': current_year_obj
    })


@login_required
@csrf_exempt
def ter_admin_reports(request, user_id):
    ter_admin = get_object_or_404(TerAdmin, representatives=user_id)
    schools = School.objects.filter(ter_admin=ter_admin, is_archived=False)
    all_schools = schools
    closters = SchoolCloster.objects.filter(schools__in=schools).distinct()
    
    # Оптимизируем запрос для отчетов, подгружая связанные данные
    s_reports = SchoolReport.objects.filter(
        school__in=schools, 
        report__is_published=True
    ).select_related(
        'school',
        'report',
        'report__year',
        'report__closter'
    ).prefetch_related(
        'answers',
        'report__sections',
        'report__sections__fields'
    ).order_by('-report__year__year', 'school__name')  # Сортировка сначала по году, затем по школе

    # Список годов для фильтрации и текущий год
    years = Year.objects.all().order_by('-year')
    current_year_obj = Year.objects.filter(is_current=True).first()

    filter = None
    session_key = f'ter_admin_reports_filter_{user_id}'
    
    # Reset filter if requested or if it's a GET request without pagination
    if 'reset' in request.GET or (request.method == 'GET' and 'page' not in request.GET):
        if session_key in request.session:
            del request.session[session_key]
        if 'reset' in request.GET:
            return HttpResponseRedirect(reverse('ter_admin_reports', args=[user_id]))
    
    # Если не задан фильтр (ни в POST, ни в сессии) — показываем отчёты текущего года
    if 'filter' not in request.POST and session_key not in request.session and current_year_obj:
        s_reports = s_reports.filter(report__year=current_year_obj)

    # Store filter parameters in session when POST request
    if 'filter' in request.POST:
        filter_params = {}
        if len(request.POST.getlist('schools')) != 0:
            schools = schools.filter(id__in=request.POST.getlist('schools'))
            s_reports = s_reports.filter(school__in=schools)
            filter_params['schools'] = request.POST.getlist('schools')
        if len(request.POST.getlist('closters')) != 0:
            schools = schools.filter(closter__in=request.POST.getlist('closters'))
            s_reports = s_reports.filter(school__in=schools)
            filter_params['closters'] = request.POST.getlist('closters')
        if len(request.POST.getlist('ed_levels')) != 0:
            schools = schools.filter(ed_level__in=request.POST.getlist('ed_levels'))
            s_reports = s_reports.filter(school__in=schools)
            filter_params['ed_levels'] = request.POST.getlist('ed_levels')
        if len(request.POST.getlist('status')) != 0:
            s_reports = s_reports.filter(status__in=request.POST.getlist('status'))
            filter_params['status'] = request.POST.getlist('status')
        if len(request.POST.getlist('years')) != 0:
            s_reports = s_reports.filter(report__year__in=request.POST.getlist('years'))
            filter_params['years'] = request.POST.getlist('years')
        
        filter = filter_params
        request.session[session_key] = filter_params
    # Use filter from session only for GET requests with pagination
    elif request.method == 'GET' and 'page' in request.GET and session_key in request.session:
        filter_params = request.session[session_key]
        filter = filter_params
        
        if 'schools' in filter_params and filter_params['schools']:
            schools = schools.filter(id__in=filter_params['schools'])
            s_reports = s_reports.filter(school__in=schools)
        if 'closters' in filter_params and filter_params['closters']:
            schools = schools.filter(closter__in=filter_params['closters'])
            s_reports = s_reports.filter(school__in=schools)
        if 'ed_levels' in filter_params and filter_params['ed_levels']:
            schools = schools.filter(ed_level__in=filter_params['ed_levels'])
            s_reports = s_reports.filter(school__in=schools)
        if 'status' in filter_params and filter_params['status']:
            s_reports = s_reports.filter(status__in=filter_params['status'])
        if 'years' in filter_params and filter_params['years']:
            s_reports = s_reports.filter(report__year__in=filter_params['years'])
    
    # Обработка пакетной отправки отчетов в МинОбр
    if 'send-reports' in request.POST:
        report_ids = request.POST.getlist('report_ids')
        if report_ids:
            # Обновляем статус выбранных отчетов с 'A' (на согласовании в ТУ/ДО) на 'B' (отправлено в МинОбр)
            SchoolReport.objects.filter(id__in=report_ids, status='A').update(status='B')
        return HttpResponseRedirect(reverse('ter_admin_reports', args=[user_id]))
    
    # Обработка запроса на экспорт данных о заполнении
    if 'export_data' in request.POST:
        # Получаем все отчеты, удовлетворяющие фильтрам (без пагинации)
        filename = f'ter_admin_{ter_admin.name}_reports_completion.xlsx'
        return export_reports_to_excel(s_reports, filename)
    
    # Pagination
    paginator = Paginator(s_reports, 20)  # 20 reports per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    return render(request, "reports/ter_admin_reports.html", {
        'user_id': user_id,
        'ter_admin': ter_admin,
        'reports': page_obj,
        'schools': all_schools,
        'closters': closters,
        'ed_levels': School.SCHOOL_LEVELS,
        'filter': filter,
        'paginator': paginator,
        'page_obj': page_obj,
        'years': years,
        'current_year': current_year_obj
    })


@login_required
@csrf_exempt
def mo_report(request, s_report_id):
    """
    Рефакторенная версия функции mo_report
    """
    s_report = get_object_or_404(SchoolReport, id=s_report_id)
    is_readonly = s_report.report.year.status == 'completed'
    current_section = request.GET.get('current_section', '')
    message = None

    if request.method == 'POST' and not is_readonly:
        if 'send-report' in request.POST:
            message = handle_send_report(s_report, 'A')
        elif request.FILES.get("file") is not None:
            id = request.POST.dict()['id']
            question = Field.objects.get(id=id)
            return handle_file_upload(request, question, s_report)
        else:
            # Блокируем все изменения через AJAX, если год завершен
            if is_readonly:
                return JsonResponse({"error": "Редактирование недоступно. Год закрыт."}, status=403)
            return handle_ajax_request(request, s_report, user_type='mo')
    
    context = get_report_context(request, s_report, current_section, message)
    return render(request, "reports/mo_report.html", context)


@login_required
@csrf_exempt
def ter_admin_report(request, ter_admin_id, s_report_id):
    """
    Рефакторенная версия функции ter_admin_report
    """
    ter_admin = get_object_or_404(TerAdmin, id=ter_admin_id)
    s_report = get_object_or_404(SchoolReport, id=s_report_id)
    is_readonly = s_report.report.year.status == 'completed'
    current_section = request.GET.get('current_section', '')
    message = None

    if request.method == 'POST' and not is_readonly:
        if 'send-report' in request.POST:
            message = handle_send_report(s_report, 'B')
        elif request.FILES.get("file") is not None:
            id = request.POST.dict()['id']
            question = Field.objects.get(id=id)
            return handle_file_upload(request, question, s_report)
        else:
            # Блокируем все изменения через AJAX, если год завершен
            if is_readonly:
                return JsonResponse({"error": "Редактирование недоступно. Год закрыт."}, status=403)
            return handle_ajax_request(request, s_report, user_type='ter_admin')

    context = get_report_context(request, s_report, current_section, message, ter_admin=ter_admin)
    return render(request, "reports/ter_admin_report.html", context)

def update_answer(request, answer_id):
    answer = get_object_or_404(Answer, id=answer_id)
    old_points = answer.points
    
    if request.method == 'POST':
        form = AnswerForm(request.POST, instance=answer)
        if form.is_valid():
            answer = form.save()
            
            # Clear related caches when answer is updated
            school_report = answer.s_report
            school = school_report.school
            year = school_report.report.year
            
            # Clear ter_admins_dash cache
            cache_key = get_cache_key('ter_admins_dash',
                year=year,
                schools=str(school.id),
                reports=str(school_report.report.id)
            )
            cache.delete(cache_key)
            
            # Clear closters_report cache
            cache_key = get_cache_key('closters_report_data',
                year=year,
                ter_admin=str(school.ter_admin.id),
                closters=str(school.closter.id) if school.closter else '',
                ed_levels=school.ed_level
            )
            cache.delete(cache_key)
            
            # Recalculate section points if needed
            if old_points != answer.points:
                section = answer.question.sections.first()
                if section:
                    section_sreport = SectionSreport.objects.get(
                        s_report=school_report,
                        section=section
                    )
                    section_sreport.points = count_section_points(section_sreport)
                    section_sreport.save()
            
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'})

def export_reports_to_excel(s_reports, filename='reports_completion.xlsx'):
    """
    Функция для экспорта данных о заполнении отчетов в Excel-формат
    
    Args:
        s_reports: QuerySet отчетов SchoolReport
        filename: Имя файла для загрузки
    
    Returns:
        HttpResponse с Excel-файлом для скачивания
    """
    # Создаем файл в памяти
    output = io.BytesIO()
    
    # Создаем рабочую книгу и лист
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # Создаем стили
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#D9EAD3',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'align': 'left',
        'valign': 'vcenter',
        'border': 1
    })
    
    percent_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'num_format': '0.00%'
    })
    
    # Задаем ширину столбцов
    worksheet.set_column(0, 0, 40)  # Школа
    worksheet.set_column(1, 1, 30)  # Кластер
    worksheet.set_column(2, 2, 25)  # Уровень образования
    worksheet.set_column(3, 3, 10)  # Год
    worksheet.set_column(4, 4, 15)  # Заполнение (%)
    worksheet.set_column(5, 5, 20)  # Заполнено полей
    worksheet.set_column(6, 6, 20)  # Всего полей
    worksheet.set_column(7, 7, 15)  # Баллы
    
    # Заголовки столбцов
    worksheet.write(0, 0, 'Школа', header_format)
    worksheet.write(0, 1, 'Кластер', header_format)
    worksheet.write(0, 2, 'Уровень образования', header_format)
    worksheet.write(0, 3, 'Год', header_format)
    worksheet.write(0, 4, 'Заполнение (%)', header_format)
    worksheet.write(0, 5, 'Заполнено полей', header_format)
    worksheet.write(0, 6, 'Всего полей', header_format)
    worksheet.write(0, 7, 'Баллы', header_format)
    
    # Данные
    row = 1
    for report in s_reports:
        # Получаем вопросы только нужных типов
        valid_types = ['LST', 'NMBR', 'PRC']
        questions = report.report.sections.all().values_list("fields", flat=True).distinct()
        valid_questions = Field.objects.filter(id__in=questions, answer_type__in=valid_types)
        total_fields = valid_questions.count()
        if total_fields == 0:
            completion_percent = 100
            filled_fields = 0
        else:
            # Подсчитываем заполненные поля
            answers = report.answers.filter(question__in=valid_questions)
            filled_fields = 0
            for answer in answers:
                if answer.question.answer_type == 'LST' and answer.option is not None:
                    filled_fields += 1
                elif answer.question.answer_type in ['NMBR', 'PRC'] and answer.number_value is not None:
                    filled_fields += 1
            completion_percent = int(round((filled_fields / total_fields) * 100))
        completion_fraction = completion_percent / 100.0
        ed_level_display = report.report.get_ed_level_display()
        worksheet.write(row, 0, report.school.name, cell_format)
        worksheet.write(row, 1, report.report.closter.name if report.report.closter else '-', cell_format)
        worksheet.write(row, 2, ed_level_display, cell_format)
        worksheet.write(row, 3, str(report.report.year), cell_format)
        worksheet.write(row, 4, completion_fraction, percent_format)
        worksheet.write(row, 5, filled_fields, cell_format)
        worksheet.write(row, 6, total_fields, cell_format)
        worksheet.write(row, 7, report.points, cell_format)
        row += 1
    
    # Закрываем рабочую книгу
    workbook.close()
    
    # Настраиваем ответ
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
