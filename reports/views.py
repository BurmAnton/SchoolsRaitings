import json
import csv
import io
import xlsxwriter
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import Sum, Max
from django.core.paginator import Paginator
from django.utils import timezone

from reports.models import Answer, Attachment, Field, Option, Report, ReportFile, ReportLink, SchoolReport, Section, SectionSreport, OptionCombination
from reports.utils import count_points, select_range_option, count_section_points, count_points_field
from reports.templatetags.reports_extras import get_completion_percent
from users.models import Group, Notification, MainPageArticle
from schools.models import School, SchoolCloster, TerAdmin
from common.utils import get_cache_key


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
    if user.is_superuser:
        return HttpResponseRedirect(reverse('admin:index'))
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
    message = None
    report = get_object_or_404(Report, id=report_id)
    school = get_object_or_404(School, id=school_id)

    # Check year status - only allow report creation/editing if year status is 'filling' or later
    if report.year.status == 'forming':
        return render(request, "reports/report_not_available.html", {
            'school': school,
            'report': report,
            'message': "Отчет в стадии формирования и пока недоступен для заполнения."
        })
    
    # If year status is 'completed', make the report read-only
    is_readonly = report.year.status == 'completed'
    
    # If year status is 'completed', show a read-only notification
    if is_readonly:
        message = "ReadOnly"
        
    current_section = request.GET.get('current_section', '')
    if current_section == "":
        current_section = report.sections.all().first().id
    else: current_section = int(current_section)

    s_report, is_new_report = SchoolReport.objects.get_or_create(
        report=report, school=school, 
    )
    
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
                    

    answers = Answer.objects.filter(s_report=s_report)
    
    if request.method == 'POST' and not is_readonly:
        if 'send-report' in request.POST:
            if s_report.status == 'C':
                s_report.status = 'A'
                s_report.save()
            message = "SendToTerAdmin"
        elif request.FILES.get("file") is not None:
            file = request.FILES.get("file")
            id = request.POST.dict()['id']

            question = Field.objects.get(id=id)
            answers = Answer.objects.filter(question=question, s_report=s_report)
            if answers.count() == 0:
                answer = Answer.objects.create(
                    s_report=s_report,
                    question=question,
                )
            elif answers.count() == 1:
                answer = answers.first()
            else:
                answer = answers.first()
                answers.exclude(id=answer.id).delete()

            file = ReportFile.objects.create(
                s_report=answer.s_report,
                answer=answer,
                file = file
            )
            return JsonResponse({
                "message": "File updated/saved successfully.",
                "question_id": question.id,
                "file_link": file.file.url,
                "filename": file.file.name,
                "file_id": file.id
            }, status=201)
        else:
            data = json.loads(request.body.decode("utf-8"))
            
            # Блокируем все изменения через AJAX, если год завершен (is_readonly=True)
            if is_readonly:
                return JsonResponse({"error": "Редактирование недоступно. Год закрыт."}, status=403)
                
            if 'file_id' in data:
                file_id = data['file_id']
                ReportFile.objects.get(id=file_id).delete()
                return JsonResponse({"message": "File deleted successfully.",}, status=201)
            elif 'link_id' in data:
                link_id = data['link_id']
                ReportLink.objects.get(id=link_id).delete()
                return JsonResponse({"message": "Link deleted successfully.",}, status=201)
            
           
            try:
                question = Field.objects.get(id=data['id'].replace('check_', ''))
            except Field.DoesNotExist:
                return JsonResponse({"error": "Поле не найдено"}, status=404)
            answers = Answer.objects.filter(question=question, s_report=s_report)
            if answers.count() == 0:
                answer = Answer.objects.create(
                    s_report=s_report,
                    question=question,
                )
            elif answers.count() == 1:
                answer = answers.first()
            else:
                answer = answers.first()
                answers.exclude(id=answer.id).delete()
            if 'link' in data:
                link = data['value']
                link = ReportLink.objects.create(
                    s_report=answer.s_report,
                    answer=answer,
                    link = link,
                )
                link.save()
                return JsonResponse({
                    "message": "Link updated/saved successfully.",
                    "question_id": question.id,
                    "link": link.link,
                    "link_id": link.id
                }, status=201)
            if question.answer_type == "LST":
                try:
                    option = Option.objects.get(id=data['value'])
                    answer.option = option
                    answer.points = option.points
                    answer.zone = option.zone
                except:
                    answer.option = None
                    answer.points = 0
                    answer.zone = "R"
            elif question.answer_type == "BL":
                
                answer.bool_value = data['value']
                answer.points = question.bool_points if answer.bool_value else 0
                answer.zone = "G" if answer.bool_value else "R"
            elif question.answer_type in ['NMBR', 'PRC']:
                answer.number_value = float(data['value'])
                r_option = select_range_option(question.range_options.all(), answer.number_value)
                if r_option == None: 
                    answer.points = 0
                    answer.zone = "R"
                else: 
                    answer.points = r_option.points
                    answer.zone = r_option.zone
            elif question.answer_type == 'MULT':
                # Обработка множественного выбора
                if 'multiple_values' in data:
                    # Очищаем предыдущие выбранные опции
                    answer.selected_options.clear()
                    selected_options_ids = data['multiple_values']
                    
                    if selected_options_ids:
                        # Получаем объекты Option по их ID
                        selected_options = list(Option.objects.filter(id__in=selected_options_ids))
                        
                        # Добавляем выбранные опции
                        answer.selected_options.add(*selected_options)
                        
                        # Сортируем номера опций для проверки комбинаций
                        option_numbers = sorted([str(opt.number) for opt in selected_options])
                        option_numbers_str = ','.join(option_numbers)
                        
                        # Проверяем, есть ли точное совпадение с комбинацией
                        try:
                            combination = OptionCombination.objects.get(
                                field=question, 
                                option_numbers=option_numbers_str
                            )
                            answer.points = combination.points
                        except OptionCombination.DoesNotExist:
                            # Если нет точного совпадения, суммируем баллы выбранных опций
                            total_points = sum(opt.points for opt in selected_options)
                            
                            # Проверяем, не превышает ли сумма максимальное значение (если оно задано)
                            if question.max_points is not None and total_points > question.max_points:
                                total_points = question.max_points
                                
                            answer.points = total_points
                        
                        # Определяем зону на основе баллов и настроек показателя
                        field = question
                        if field.yellow_zone_min is not None and field.green_zone_min is not None:
                            if answer.points < field.yellow_zone_min:
                                answer.zone = 'R'
                            elif answer.points >= field.green_zone_min:
                                answer.zone = 'G'
                            else:
                                answer.zone = 'Y'
                        else:
                            # Если в показателе не заданы зоны, попробуем использовать зоны из раздела
                            section = field.sections.first()
                            if section and section.yellow_zone_min is not None and section.green_zone_min is not None:
                                if answer.points < section.yellow_zone_min:
                                    answer.zone = 'R'
                                elif answer.points >= section.green_zone_min:
                                    answer.zone = 'G'
                                else:
                                    answer.zone = 'Y'
                            else:
                                # Если нигде не заданы зоны, то определяем по наличию баллов
                                answer.zone = 'G' if answer.points > 0 else 'R'
                    else:
                        # Если ничего не выбрано, обнуляем баллы
                        answer.points = 0
                        answer.zone = 'R'
            answer.save()

            # Clear dashboard caches when answer is updated
            cache_key = get_cache_key('ter_admins_dash',
                year=s_report.report.year,
                schools=','.join(sorted(str(s.id) for s in School.objects.filter(ter_admin=school.ter_admin, is_archived=False))),
                reports=','.join(sorted(str(r.id) for r in Report.objects.filter(year=s_report.report.year)))
            )
            cache.delete(cache_key)
            
            # Clear closters_report cache
            cache_key = get_cache_key('closters_report_data',
                year=s_report.report.year,
                ter_admin=str(school.ter_admin.id),
                closters=str(school.closter.id) if school.closter else '',
                ed_levels=school.ed_level
            )
            cache.delete(cache_key)

            list_answers = Answer.objects.filter(s_report=s_report, question__answer_type='LST', option=None)
            if len(list_answers) == 0:
                s_report.is_ready = True
            else: s_report.is_ready = False
            zone, points_sum = count_points(s_report)
            
            if zone != 'W':
                s_report.zone = zone
                a_zone = answer.zone
            else:
                a_zone = 'W'

            s_report.points = points_sum
            s_report.save()

            section = Section.objects.get(fields=question.id, report=s_report.report)
         
            return JsonResponse(
                {
                    "message": "Question changed successfully.", 
                    "points": str(answer.points), 
                    "ready":s_report.is_ready,
                    "zone": zone, 
                    "report_points": s_report.points,
                    "answer_z": a_zone,
                    "section_z": count_section_points(s_report, section),
                
                }, 
                status=201
            )

    return render(request, "reports/report.html", {
        'school': school,
        'report': report,
        'current_section': current_section,
        'message': message,
        's_report': s_report,
        'answers': answers,
        'is_readonly': is_readonly,
    })


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
    ).order_by('-report__year', 'school__name')  # Добавляем сортировку для пагинации

    filter = None
    # Reset filter if requested
    if 'reset' in request.GET:
        if 'mo_reports_filter' in request.session:
            del request.session['mo_reports_filter']
        return HttpResponseRedirect(reverse('mo_reports'))
    
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
        
        filter = filter_params
        request.session['mo_reports_filter'] = filter_params
    # Use filter from session for GET requests (pagination)
    elif request.method == 'GET' and 'mo_reports_filter' in request.session:
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
        'page_obj': page_obj
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
    )

    filter = None
    # Reset filter if requested
    if 'reset' in request.GET:
        if 'ter_admin_reports_filter_{user_id}' in request.session:
            del request.session[f'ter_admin_reports_filter_{user_id}']
        return HttpResponseRedirect(reverse('ter_admin_reports', args=[user_id]))
    
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
        if len(request.POST.getlist('status')) != 0:
            s_reports = s_reports.filter(status__in=request.POST.getlist('status'))
            filter_params['status'] = request.POST.getlist('status')
        
        filter = filter_params
        request.session[f'ter_admin_reports_filter_{user_id}'] = filter_params
    # Use filter from session for GET requests (pagination)
    elif request.method == 'GET' and f'ter_admin_reports_filter_{user_id}' in request.session:
        filter_params = request.session[f'ter_admin_reports_filter_{user_id}']
        filter = filter_params
        
        if 'schools' in filter_params and filter_params['schools']:
            schools = schools.filter(id__in=filter_params['schools'])
            s_reports = s_reports.filter(school__in=schools)
        if 'closters' in filter_params and filter_params['closters']:
            schools = schools.filter(closter__in=filter_params['closters'])
            s_reports = s_reports.filter(school__in=schools)
        if 'status' in filter_params and filter_params['status']:
            s_reports = s_reports.filter(status__in=filter_params['status'])
    
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
        'filter': filter,
        'paginator': paginator,
        'page_obj': page_obj
    })


@login_required
@csrf_exempt
def mo_report(request, s_report_id):
    message = None
    s_report = get_object_or_404(SchoolReport, id=s_report_id)
    answers = Answer.objects.filter(s_report=s_report)
    
    # If year status is 'completed', make the report read-only
    is_readonly = s_report.report.year.status == 'completed'
    
    # If year status is 'completed', show a read-only notification
    if is_readonly:
        message = "ReadOnly"
    
    current_section = request.GET.get('current_section', '')
    if current_section == "":
        current_section = s_report.report.sections.all().first().id
    else: current_section = int(current_section)

    if request.method == 'POST' and not is_readonly:
        if 'send-report' in request.POST:
            s_report.status = 'A'
            s_report.save()
            message = "SendToTerAdmin"
        elif request.FILES.get("file") is not None:
            file = request.FILES.get("file")
            id = request.POST.dict()['id']

            question = Field.objects.get(id=id)
            answer = Answer.objects.filter(question=question, s_report=s_report).first()
            file = ReportFile.objects.create(
                s_report=answer.s_report,
                answer=answer,
                file=file
            )
            return JsonResponse({
                "message": "File updated/saved successfully.",
                "question_id": question.id,
                "file_link": file.file.url,
                "filename": file.file.name,
                "file_id": file.id
            }, status=201)
        else:
            data = json.loads(request.body.decode("utf-8"))
            
            # Блокируем все изменения через AJAX, если год завершен (is_readonly=True)
            if is_readonly:
                return JsonResponse({"error": "Редактирование недоступно. Год закрыт."}, status=403)
                
            if 'file_id' in data:
                file_id = data['file_id']
                ReportFile.objects.get(id=file_id).delete()
                return JsonResponse({"message": "File deleted successfully.",}, status=201)
            elif 'link_id' in data:
                link_id = data['link_id']
                ReportLink.objects.get(id=link_id).delete()
                return JsonResponse({"message": "Link deleted successfully.",}, status=201)
            
            question = Field.objects.get(id=data['id'].replace('check_', ''))
            answer = Answer.objects.filter(question=question, s_report=s_report).first()
            if question.answer_type == "LST":
                try:
                    option = Option.objects.get(id=data['value'])
                    answer.option = option
                    answer.points = option.points
                    answer.zone = option.zone
                except:
                    answer.option = None
                    answer.points = 0
                    answer.zone = "R"
            elif question.answer_type == "BL":
                answer.bool_value = data['value']
                answer.points = question.bool_points if answer.bool_value else 0
                answer.zone = "G" if answer.bool_value else "R"
            elif question.answer_type in ['NMBR', 'PRC']:
                answer.number_value = float(data['value'])
                r_option = select_range_option(question.range_options.all(), answer.number_value)
                if r_option == None: 
                    answer.points = 0
                    answer.zone = "R"
                else: 
                    answer.points = r_option.points
                    answer.zone = r_option.zone
            elif question.answer_type == 'MULT':
                # Обработка множественного выбора
                if 'multiple_values' in data:
                    # Очищаем предыдущие выбранные опции
                    answer.selected_options.clear()
                    selected_options_ids = data['multiple_values']
                    
                    if selected_options_ids:
                        # Получаем объекты Option по их ID
                        selected_options = list(Option.objects.filter(id__in=selected_options_ids))
                        
                        # Добавляем выбранные опции
                        answer.selected_options.add(*selected_options)
                        
                        # Сортируем номера опций для проверки комбинаций
                        option_numbers = sorted([str(opt.number) for opt in selected_options])
                        option_numbers_str = ','.join(option_numbers)
                        
                        # Проверяем, есть ли точное совпадение с комбинацией
                        try:
                            combination = OptionCombination.objects.get(
                                field=question, 
                                option_numbers=option_numbers_str
                            )
                            answer.points = combination.points
                        except OptionCombination.DoesNotExist:
                            # Если нет точного совпадения, суммируем баллы выбранных опций
                            total_points = sum(opt.points for opt in selected_options)
                            
                            # Проверяем, не превышает ли сумма максимальное значение (если оно задано)
                            if question.max_points is not None and total_points > question.max_points:
                                total_points = question.max_points
                                
                            answer.points = total_points
                        
                        # Определяем зону на основе баллов и настроек показателя
                        field = question
                        if field.yellow_zone_min is not None and field.green_zone_min is not None:
                            if answer.points < field.yellow_zone_min:
                                answer.zone = 'R'
                            elif answer.points >= field.green_zone_min:
                                answer.zone = 'G'
                            else:
                                answer.zone = 'Y'
                        else:
                            # Если в показателе не заданы зоны, попробуем использовать зоны из раздела
                            section = field.sections.first()
                            if section and section.yellow_zone_min is not None and section.green_zone_min is not None:
                                if answer.points < section.yellow_zone_min:
                                    answer.zone = 'R'
                                elif answer.points >= section.green_zone_min:
                                    answer.zone = 'G'
                                else:
                                    answer.zone = 'Y'
                            else:
                                # Если нигде не заданы зоны, то определяем по наличию баллов
                                answer.zone = 'G' if answer.points > 0 else 'R'
                    else:
                        # Если ничего не выбрано, обнуляем баллы
                        answer.points = 0
                        answer.zone = 'R'
            answer.is_mod_by_mo = True #####
            answer.save()

            list_answers = Answer.objects.filter(s_report=s_report, question__answer_type='LST', option=None)
            if len(list_answers) == 0:
                s_report.is_ready = True
            else: s_report.is_ready = False
            zone, points_sum = count_points(s_report)
            
            if zone != 'W':
                s_report.zone = zone
                a_zone = answer.zone
            else:
                a_zone = 'W'

            s_report.points = points_sum
            s_report.save()

            section = Section.objects.get(fields=question.id, report=s_report.report)

            return JsonResponse(
                {
                    "message": "Question changed successfully.", 
                    "points": str(answer.points), 
                    "ready":s_report.is_ready,
                    "zone": zone, 
                    "report_points": s_report.points,
                    "answer_z": a_zone,
                    "section_z": count_section_points(s_report, section),
                
                }, 
                status=201
            )
    
    return render(request, "reports/mo_report.html", {
        'message': message,
        'school': s_report.school,
        'report': s_report,
        'answers': answers,
        'current_section': current_section,
        'is_readonly': is_readonly,
    })


@login_required
@csrf_exempt
def ter_admin_report(request, ter_admin_id, s_report_id):
    message = None
    ter_admin = get_object_or_404(TerAdmin, id=ter_admin_id)
    s_report = get_object_or_404(SchoolReport, id=s_report_id)
    answers = Answer.objects.filter(s_report=s_report)

    # If year status is 'completed', make the report read-only
    is_readonly = s_report.report.year.status == 'completed'

    # If year status is 'completed', show a read-only notification
    if is_readonly:
        message = "ReadOnly"

    current_section = request.GET.get('current_section', '')
    if current_section == "":
        current_section = s_report.report.sections.all().first().id
    else: current_section = int(current_section)
    
    if request.method == 'POST' and not is_readonly:
        if 'send-report' in request.POST:
            s_report.status = 'B'
            s_report.save()
            message = "SendToMinObr"
        elif request.FILES.get("file") is not None:
            file = request.FILES.get("file")
            id = request.POST.dict()['id']

            question = Field.objects.get(id=id)
            answer = Answer.objects.filter(question=question, s_report=s_report).first()
            file = ReportFile.objects.create(
                s_report=answer.s_report,
                answer=answer,
                file=file
            )
            return JsonResponse({
                "message": "File updated/saved successfully.",
                "question_id": question.id,
                "file_link": file.file.url,
                "filename": file.file.name,
                "file_id": file.id
            }, status=201)
        else:
            data = json.loads(request.body.decode("utf-8"))
            if 'file_id' in data:
                file_id = data['file_id']
                ReportFile.objects.get(id=file_id).delete()
                return JsonResponse({"message": "File deleted successfully.",}, status=201)
            elif 'link_id' in data:
                link_id = data['link_id']
                ReportLink.objects.get(id=link_id).delete()
                return JsonResponse({"message": "Link deleted successfully.",}, status=201)
            elif 'check_answer' in data:
                # Обработка проверки показателя
                answer_id = data['answer_id']
                is_checked = data['is_checked']

                try:
                    answer = Answer.objects.get(id=answer_id)
                    answer.is_checked = is_checked
                    if is_checked:
                        answer.checked_by = request.user
                        answer.checked_at = timezone.now()
                    else:
                        answer.checked_by = None
                        answer.checked_at = None
                    answer.save()
                    return JsonResponse({
                        "message": "Answer check status updated successfully.",
                        "checked_by": answer.checked_by.get_full_name() if answer.checked_by else None,
                        "checked_at": answer.checked_at.strftime("%d.%m.%Y %H:%M") if answer.checked_at else None
                    }, status=201)
                except Answer.DoesNotExist:
                    return JsonResponse({"error": "Ответ не найден"}, status=404)
            
            # Блокируем все изменения через AJAX, если год завершен (is_readonly=True)
            if is_readonly:
                return JsonResponse({"error": "Редактирование недоступно. Год закрыт."}, status=403)
            
            try:
                question = Field.objects.get(id=data['id'].replace('check_', ''))
            except Field.DoesNotExist:
                return JsonResponse({"error": "Поле не найдено"}, status=404)
            answer = Answer.objects.filter(question=question, s_report=s_report).first()
            if 'link' in data:
                link = data['value']
                link = ReportLink.objects.create(
                    s_report=answer.s_report,
                    answer=answer,
                    link=link,
                )
                link.save()
                return JsonResponse({
                    "message": "Link updated/saved successfully.",
                    "question_id": question.id,
                    "link": link.link,
                    "link_id": link.id
                }, status=201)
            if question.answer_type == "LST":
                try:
                    option = Option.objects.get(id=data['value'])
                    answer.option = option
                    answer.points = option.points
                    answer.zone = option.zone
                except:
                    answer.option = None
                    answer.points = 0
                    answer.zone = "R"
            elif question.answer_type == "BL":
                answer.bool_value = data['value']
                answer.points = question.bool_points if answer.bool_value else 0
                answer.zone = "G" if answer.bool_value else "R"
            elif question.answer_type in ['NMBR', 'PRC']:
                answer.number_value = float(data['value'])
                r_option = select_range_option(question.range_options.all(), answer.number_value)
                if r_option == None: 
                    answer.points = 0
                    answer.zone = "R"
                else: 
                    answer.points = r_option.points
                    answer.zone = r_option.zone
            elif question.answer_type == 'MULT':
                # Обработка множественного выбора
                if 'multiple_values' in data:
                    # Очищаем предыдущие выбранные опции
                    answer.selected_options.clear()
                    selected_options_ids = data['multiple_values']
                    
                    if selected_options_ids:
                        # Получаем объекты Option по их ID
                        selected_options = list(Option.objects.filter(id__in=selected_options_ids))
                        
                        # Добавляем выбранные опции
                        answer.selected_options.add(*selected_options)
                        
                        # Сортируем номера опций для проверки комбинаций
                        option_numbers = sorted([str(opt.number) for opt in selected_options])
                        option_numbers_str = ','.join(option_numbers)
                        
                        # Проверяем, есть ли точное совпадение с комбинацией
                        try:
                            combination = OptionCombination.objects.get(
                                field=question, 
                                option_numbers=option_numbers_str
                            )
                            answer.points = combination.points
                        except OptionCombination.DoesNotExist:
                            # Если нет точного совпадения, суммируем баллы выбранных опций
                            total_points = sum(opt.points for opt in selected_options)
                            
                            # Проверяем, не превышает ли сумма максимальное значение (если оно задано)
                            if question.max_points is not None and total_points > question.max_points:
                                total_points = question.max_points
                                
                            answer.points = total_points
                        
                        # Определяем зону на основе баллов и настроек показателя
                        field = question
                        if field.yellow_zone_min is not None and field.green_zone_min is not None:
                            if answer.points < field.yellow_zone_min:
                                answer.zone = 'R'
                            elif answer.points >= field.green_zone_min:
                                answer.zone = 'G'
                            else:
                                answer.zone = 'Y'
                        else:
                            # Если в показателе не заданы зоны, попробуем использовать зоны из раздела
                            section = field.sections.first()
                            if section and section.yellow_zone_min is not None and section.green_zone_min is not None:
                                if answer.points < section.yellow_zone_min:
                                    answer.zone = 'R'
                                elif answer.points >= section.green_zone_min:
                                    answer.zone = 'G'
                                else:
                                    answer.zone = 'Y'
                            else:
                                # Если нигде не заданы зоны, то определяем по наличию баллов
                                answer.zone = 'G' if answer.points > 0 else 'R'
                    else:
                        # Если ничего не выбрано, обнуляем баллы
                        answer.points = 0
                        answer.zone = 'R'
            answer.is_mod_by_ter = True
            answer.save()

            list_answers = Answer.objects.filter(s_report=s_report, question__answer_type='LST', option=None)
            if len(list_answers) == 0:
                s_report.is_ready = True
            else: s_report.is_ready = False
            zone, points_sum = count_points(s_report)
            
            if zone != 'W':
                s_report.zone = zone
                a_zone = answer.zone
            else:
                a_zone = 'W'

            s_report.points = points_sum
            s_report.save()

            section = Section.objects.get(fields=question.id, report=s_report.report)

            return JsonResponse(
                {
                    "message": "Question changed successfully.", 
                    "points": str(answer.points), 
                    "ready":s_report.is_ready,
                    "zone": zone, 
                    "report_points": s_report.points,
                    "answer_z": a_zone,
                    "section_z": count_section_points(s_report, section),
                }, 
                status=201
            )

    return render(request, "reports/ter_admin_report.html", {
        'message': message,
        'ter_admin': ter_admin,
        'school': s_report.school,
        'report': s_report,
        'answers': answers,
        'current_section': current_section,
        'is_readonly': is_readonly,
    })

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
        # Получаем процент заполнения
        completion_data = get_completion_percent(report)
        completion_percent = completion_data[0] if isinstance(completion_data, tuple) else completion_data
        
        # Делим на 100, так как формат Excel требует десятичную дробь
        completion_fraction = completion_percent / 100.0
        
        # Получаем название уровня образования
        ed_level_display = report.report.get_ed_level_display()
        
        # Получаем количество заполненных и общее количество полей
        all_answers = Answer.objects.filter(s_report=report)
        total_fields = all_answers.count()
        
        # Считаем заполненные поля разных типов
        empty_lst_fields = all_answers.filter(question__answer_type='LST', option=None).count()
        empty_bl_fields = all_answers.filter(question__answer_type='BL', bool_value=None).count()
        empty_nmbr_fields = all_answers.filter(
            question__answer_type__in=['NMBR', 'PRC'], 
            number_value=None
        ).count()
        # Для MULT считаем ответы без выбранных опций
        empty_mult_fields = 0
        for answer in all_answers.filter(question__answer_type='MULT'):
            if not answer.selected_options.exists():
                empty_mult_fields += 1
        
        # Общее количество незаполненных полей
        empty_fields = empty_lst_fields + empty_bl_fields + empty_nmbr_fields + empty_mult_fields
        filled_fields = total_fields - empty_fields
        
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