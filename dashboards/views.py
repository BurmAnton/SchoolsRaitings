from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from reports.models import Report, SchoolReport
from schools.models import SchoolCloster, School, TerAdmin

# Create your views here.
@login_required
def ter_admins_reports(request):
    reports = Report.objects.all()

    return render(request, "dashboards/ter_admins_reports.html", {
        'reports': reports,
    })


@login_required
@csrf_exempt
def ter_admins_dash(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    # years = Report.objects.values_list('year', flat=True).distinct()

    ter_admins = TerAdmin.objects.all()
    closters = SchoolCloster.objects.all()
    ed_levels = {
        'A': "1 — 11 классы",
        'M': "1 — 9 классы",
        'S': "1 — 4 классы",
        'MG': "5 — 11 классы",
        'G': "10 — 11 классы",
    }

    filter = {}
    if request.method == 'POST':
        # year = int(request.POST["year"])
        schools = School.objects.all()
        ter_admins_f = request.POST.getlist("ter_admins")
        if len(ter_admins_f) != 0:
            schools = schools.filter(ter_admin__in=ter_admins_f)
            filter['ter_admins'] = ter_admins_f
        closters_f = request.POST.getlist("closters")
        if len(closters_f) != 0:
            schools = schools.filter(closter__in=closters_f)
            filter['closters'] = closters_f
        ed_levels_f = request.POST.getlist("ed_levels")
        if len(ed_levels_f) != 0:
            schools = schools.filter(ed_level__in=ed_levels_f)
            filter['ed_levels'] = ed_levels_f

        schools_reports = SchoolReport.objects.filter(report=report, school__in=schools)
    else:
        schools_reports = SchoolReport.objects.filter(report=report)

    return render(request, "dashboards/ter_admins_dash.html", {
        #'years': years,
        "report": report,
        "filter": filter,
        'ter_admins': ter_admins,
        'closters': closters,
        'ed_levels': ed_levels,
        'schools_reports': schools_reports
    })