import json
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from reports.models import Answer, Field, Option, Question, Report, ReportZone, SchoolReport
from users.models import Group
from schools.models import School


@login_required
def index(request):
    user = request.user
    principal_group = Group.objects.get(name='Представитель школы')
    if user.groups.filter(id=principal_group.id).count() == 1:
        return HttpResponseRedirect(reverse('reports', kwargs={'school_id': user.school.id}))

    return render(request, "reports/index.html")


def reports(request, school_id):
    school = get_object_or_404(School, id=school_id)
    report_zones = ReportZone.objects.filter(closter=school.closter)
    reports = Report.objects.filter(zones__in=report_zones).order_by('year').distinct()
    s_reports = SchoolReport.objects.filter(school=school)
    reports_list = []
    for report in reports:
        if s_reports.filter(report=report).count() != 0:
            reports_list.append([report, s_reports[0]])
        else:
            reports_list.append([report, None])

    return render(request, "reports/reports.html", {
        'school': school,
        'reports': reports_list
    })


@csrf_exempt
def report(request, report_id, school_id):
    report = get_object_or_404(Report, id=report_id)
    school = get_object_or_404(School, id=school_id)

    current_section = request.GET.get('current_section', '')
    if current_section == "":
        current_section = report.sections.all()[0].id
    else: current_section = int(current_section)

    s_report, is_new_report = SchoolReport.objects.get_or_create(
        report=report, school=school
    )
    if is_new_report:
        sections = report.sections.all()
        fields = Field.objects.filter(section__in=sections)
        for question in Question.objects.filter(field__in=fields):
            Answer.objects.create(
                s_report=s_report,
                question=question,
            )
    answers = Answer.objects.filter(s_report=s_report)

    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        question = Question.objects.get(id=data['id'])
        answer = Answer.objects.get(question=question, s_report=s_report)
        if question.answer_type == "LST":
            try: option = Option.objects.get(id=data['value'])
            except: option = None
            answer.option = option
            answer.points = option.points
        elif question.answer_type == "BL":
            answer.bool_value = data['value']
            answer.points = question.bool_points if answer.bool_value else 0
        answer.save()

        return JsonResponse(
            {"message": "Question changed successfully."}, 
            status=201
        )

    return render(request, "reports/report.html", {
        'school': school,
        'report': s_report,
        'answers': answers,
        'current_section': current_section
    })
    