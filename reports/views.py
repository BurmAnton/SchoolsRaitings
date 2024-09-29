import json
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from reports.models import Answer, Attachment, Field, Option, Report, ReportFile, SchoolReport, Section
from reports.utils import count_points, select_range_option, count_section_points, count_points_field
from users.models import Group, Notification, MainPageArticle
from schools.models import School, SchoolCloster, TerAdmin


@login_required
def index(request):
    user = request.user
    return HttpResponseRedirect(reverse('start'))
    principal_group = Group.objects.get(name='Представитель школы')
    if user.groups.filter(id=principal_group.id).count() == 1:
        return HttpResponseRedirect(reverse('reports', kwargs={'school_id': user.school.id}))
    teradmin_group = Group.objects.get(name='Представитель ТУ/ДО')
    if user.groups.filter(id=teradmin_group.id).count() == 1:
        return HttpResponseRedirect(reverse('ter_admin_reports', kwargs={'user_id': user.id}))
    mo_group = Group.objects.get(name='Представитель МинОбр')
    if user.groups.filter(id=mo_group.id).count() == 1:
        return HttpResponseRedirect(reverse('mo_reports'))
    if user.is_superuser:
        return HttpResponseRedirect(reverse('admin:index'))


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
    reports = Report.objects.filter(closter=school.closter, ed_level=school.ed_level).order_by('year').distinct()
    s_reports = SchoolReport.objects.filter(school=school)
    reports_list = []
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    for notification in notifications:
        notification.is_read = True
        notification.save()
    for report in reports:
        if s_reports.filter(report=report).count() != 0:
            reports_list.append([report, s_reports[0]])
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
        report=report, school=school
    )
    
    sections = report.sections.all()
    for question in Field.objects.filter(sections__in=sections):
        Answer.objects.get_or_create(
            s_report=s_report,
            question=question,
        )

    answers = Answer.objects.filter(s_report=s_report)
    
    if request.method == 'POST':
        if 'send-report' in request.POST:
            s_report.status = 'A'
            s_report.save()
            message = "SendToTerAdmin"
        elif request.FILES.get("file") is not None:
            file = request.FILES.get("file")
            id = request.POST.dict()['id']

            question = Field.objects.get(id=id)
            answer = Answer.objects.get(question=question, s_report=s_report)
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
            answer = Answer.objects.get(question=question, s_report=s_report)
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
    schools = School.objects.all()
    ter_admins = TerAdmin.objects.all()
    closters = SchoolCloster.objects.filter(schools__in=schools)
    s_reports = SchoolReport.objects.filter(school__in=schools)
    
    filter = None
    if 'filter' in request.POST:
        if len(request.POST.getlist('ter_admins')) != 0:
            schools = schools.filter(ter_admin__in=request.POST.getlist('ter_admins'))
            s_reports = s_reports.filter(school__in=schools)
        if len(request.POST.getlist('closters')) != 0:
            schools = schools.filter(closter__in=request.POST.getlist('closters'))
            s_reports = s_reports.filter(school__in=schools)
        if len(request.POST.getlist('status')) != 0:
            s_reports = s_reports.filter(status__in=request.POST.getlist('status'))
        filter = {
            'ter_admins': request.POST.getlist('ter_admins'),
            'closters': request.POST.getlist('closters'),
            'status': request.POST.getlist('status')
        }

    return render(request, "reports/mo_reports.html", {
        'reports': s_reports,
        'ter_admins': ter_admins,
        'closters': closters,
        'filter': filter
    })


@login_required
@csrf_exempt
def ter_admin_reports(request, user_id):
    ter_admin = get_object_or_404(TerAdmin, representative=user_id)
    schools = School.objects.filter(ter_admin=ter_admin)
    all_schools = schools
    closters = SchoolCloster.objects.filter(schools__in=schools)
    s_reports = SchoolReport.objects.filter(school__in=schools)  

    filter = None
    if 'filter' in request.POST:
        if len(request.POST.getlist('schools')) != 0:
            schools = schools.filter(id__in=request.POST.getlist('schools'))
            s_reports = s_reports.filter(school__in=schools)
        if len(request.POST.getlist('closters')) != 0:
            schools = schools.filter(closter__in=request.POST.getlist('closters'))
            s_reports = s_reports.filter(school__in=schools)
        if len(request.POST.getlist('status')) != 0:
            s_reports = s_reports.filter(status__in=request.POST.getlist('status'))
        filter = {
            'schools': request.POST.getlist('schools'),
            'closters': request.POST.getlist('closters'),
            'status': request.POST.getlist('status')
        }

    return render(request, "reports/ter_admin_reports.html", {
        'user_id': user_id,
        'ter_admin': ter_admin,
        'reports': s_reports,
        'schools': all_schools,
        'closters': closters,
        'filter': filter
    })


@login_required
@csrf_exempt
def mo_report(request, s_report_id):
    message = None
    s_report = get_object_or_404(SchoolReport, id=s_report_id)
    answers = Answer.objects.filter(s_report=s_report)
    
    current_section = request.GET.get('current_section', '')
    if current_section == "":
        current_section = s_report.report.sections.all()[0].id
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
            answer = Answer.objects.get(question=question, s_report=s_report)
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
            answer = Answer.objects.get(question=question, s_report=s_report)
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
        current_section = s_report.report.sections.all()[0].id
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
            answer = Answer.objects.get(question=question, s_report=s_report)
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
            answer = Answer.objects.get(question=question, s_report=s_report)
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