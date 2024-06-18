from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponseRedirect

from reports.models import Report, SchoolReport
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
    reports = Report.objects.filter(closter=school.closter).order_by('year')
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


def report(request, report_id, school_id):
    report = get_object_or_404(Report, id=report_id)
    school = get_object_or_404(School, id=school_id)

    s_report, _ = SchoolReport.objects.get_or_create(
        report=report, school=school
    )

    return render(request, "reports/report.html", {
        'school': school,
        'report': s_report
    })
    