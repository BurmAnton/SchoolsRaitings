import json
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import Sum, Max
from django.core.paginator import Paginator

from reports.models import Answer, Attachment, Field, Option, Report, ReportFile, ReportLink, SchoolReport, Section, SectionSreport, OptionCombination
from reports.utils import count_points, select_range_option, count_section_points, count_points_field
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
    reports = Report.objects.filter(closter=school.closter, ed_level=school.ed_level, is_published=True).order_by('year').distinct()
    s_reports = SchoolReport.objects.filter(school=school)
    reports_list = []
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    for notification in notifications:
        notification.is_read = True
        notification.save()
    for report in reports:
        if s_reports.filter(report=report).count() != 0:
            reports_list.append([report, s_reports.filter(report=report)[0]])
        else:
            reports_list.append([report, None])

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
    
    if request.method == 'POST':
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
            if 'file_id' in data:
                file_id = data['file_id']
                ReportFile.objects.get(id=file_id).delete()
                return JsonResponse({"message": "File deleted successfully.",}, status=201)
            elif 'link_id' in data:
                link_id = data['link_id']
                ReportLink.objects.get(id=link_id).delete()
                return JsonResponse({"message": "Link deleted successfully.",}, status=201)
            
           
            question = Field.objects.get(id=data['id'])
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
        'message': message,
        'school': school,
        'report': s_report,
        'answers': answers,
        'current_section': current_section
    })


@login_required
@csrf_exempt
def mo_reports(request):
    schools = School.objects.filter(is_archived=False)
    ter_admins = TerAdmin.objects.all()
    closters = SchoolCloster.objects.filter(schools__in=schools).distinct()
    s_reports = SchoolReport.objects.filter(school__in=schools, report__is_published=True)
    
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
        if 'status' in filter_params and filter_params['status']:
            s_reports = s_reports.filter(status__in=filter_params['status'])
            
    if 'send-reports' in request.POST:
        s_reports.filter(status='B').update(status='D')
        return HttpResponseRedirect(reverse('mo_reports'))
    
    # Pagination
    paginator = Paginator(s_reports, 20)  # 20 reports per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
        
    return render(request, "reports/mo_reports.html", {
        'reports': page_obj,
        'ter_admins': ter_admins,
        'closters': closters,
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
    s_reports = SchoolReport.objects.filter(school__in=schools, report__is_published=True)

    filter = None
    # Reset filter if requested
    if 'reset' in request.GET:
        if f'ter_admin_reports_filter_{user_id}' in request.session:
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
    
    current_section = request.GET.get('current_section', '')
    if current_section == "":
        current_section = s_report.report.sections.all().first().id
    else: current_section = int(current_section)

    if request.method == 'POST':
        if 'send-report' in request.POST:
            s_report.status = 'D'
            s_report.save()
            message = "Approved"
        elif request.FILES.get("file") is not None:
            file = request.FILES.get("file")
            id = request.POST.dict()['id']

            question = Field.objects.get(id=id)
            answer = Answer.objects.filter(question=question, s_report=s_report).first()
            answer.file = file
            answer.save()
            return JsonResponse({
                "message": "File updated/saved successfully.",
                "question_id": question.id,
                "file_link": answer.file.url
            }, status=201)
        else:
            data = json.loads(request.body.decode("utf-8"))
            question = Field.objects.get(id=data['id'])
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
        'current_section': current_section
    })


@login_required
@csrf_exempt
def ter_admin_report(request, ter_admin_id, s_report_id):
    message = None
    ter_admin = get_object_or_404(TerAdmin, id=ter_admin_id)
    s_report = get_object_or_404(SchoolReport, id=s_report_id)
    answers = Answer.objects.filter(s_report=s_report)

    current_section = request.GET.get('current_section', '')
    if current_section == "":
        current_section = s_report.report.sections.all().first().id
    else: current_section = int(current_section)
    
    if request.method == 'POST':
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
            
            question = Field.objects.get(id=data['id'])
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
            answer.is_mod_by_ter = True #####
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
        'current_section': current_section
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