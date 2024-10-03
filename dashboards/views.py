from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from reports.models import Report, SchoolReport, Section
from reports.utils import count_section_points
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
def ter_admins_dash(request):
    ter_admins = TerAdmin.objects.all()
    closters = SchoolCloster.objects.all()
    ed_levels = {
        'A': "1 — 11 классы",
        'M': "1 — 9 классы",
        'S': "1 — 4 классы",
        'MG': "5 — 11 классы",
        'G': "10 — 11 классы",
    }
    # Get all unique years from Report
    years = Report.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    filter = {}
    schools = School.objects.all()


    if request.method != 'POST':
        year = years[0]
        reports = Report.objects.filter(year=year)
    else:
        year = int(request.POST["year"])
        reports = Report.objects.filter(year=year)  
        ter_admins_f = request.POST["year"]
        schools = schools.filter(ter_admin=ter_admins_f)
        filter['ter_admins'] = ter_admins_f
        closters_f = request.POST.getlist("closters")
        if len(closters_f) != 0:
            schools = schools.filter(closter__in=closters_f)
            filter['closters'] = closters_f
        ed_levels_f = request.POST.getlist("ed_levels")
        if len(ed_levels_f) != 0:
            schools = schools.filter(ed_level__in=ed_levels_f)
            filter['ed_levels'] = ed_levels_f

    schools_reports = SchoolReport.objects.filter(report__in=reports, school__in=schools)
    sections = Section.objects.filter(report__in=reports).distinct('name')
    
    return render(request, "dashboards/ter_admins_dash.html", {
        "years": years,
        "selected_year": year,
        "reports": reports,   
        "filter": filter,
        'ter_admins': ter_admins,
        'closters': closters,
        'ed_levels': ed_levels,
        'schools_reports': schools_reports,
        'sections': sections
    })


@login_required
@csrf_exempt
def school_report(request):
    ter_admins = TerAdmin.objects.all()
    years = Report.objects.values_list('year', flat=True).distinct().order_by('year')
    school = None
    s_reports = None
    sections = None
    stats = {}
    filter = {}
    if request.method == 'POST':
        school = School.objects.get(id=request.POST["school"])
        f_years = request.POST.getlist("years")
        reports = Report.objects.filter(year__in=f_years)
        sections = Section.objects.filter(report__in=reports).distinct('name')
        s_reports = SchoolReport.objects.filter(report__in=reports, school=school).order_by('report__year')
        filter = {
            'years': f_years,
            'school': school.id,
            'ter_admin': school.ter_admin.id
        }
        for year in f_years:
            stats[year] = {
                'green_zone': SchoolReport.objects.filter(zone='G', report__year=year).count(),
                'yellow_zone': SchoolReport.objects.filter(zone='Y', report__year=year).count(),
                'red_zone': SchoolReport.objects.filter(zone='R', report__year=year).count(),
            }
            for section in sections:
                stats[year][section.name] = {
                    'green_zone': 0,
                    'yellow_zone': 0,
                    'red_zone': 0,
                }
                s_reports_year = s_reports.filter(report__year=year)
                for s_report in s_reports_year:
                    color = count_section_points(s_report, section)
                    if color == 'G':
                        stats[year][section.name]['green_zone'] += 1
                    elif color == 'Y':
                        stats[year][section.name]['yellow_zone'] += 1
                    elif color == 'R':
                        stats[year][section.name]['red_zone'] += 1
                                
    return render(request, "dashboards/school_report.html", {
        'years': years,
        'ter_admins': ter_admins,
        'dash_school': school,
        's_reports': s_reports,
        'filter': filter,
        'sections': sections,
        'stats': stats
    })


def closters_report(request, year=2024):
    ter_admins = TerAdmin.objects.all()
    years = Report.objects.values_list('year', flat=True).distinct().order_by('year')
    closters = SchoolCloster.objects.all()
    ed_levels = {
        'A': "1 — 11 классы",
        'M': "1 — 9 классы",
        'S': "1 — 4 классы",
        'MG': "5 — 11 классы",
        'G': "10 — 11 классы",
    }
    s_reports = SchoolReport.objects.filter(report__year=year)
    sections = Section.objects.filter(report__year=year).distinct('name')

    schools = School.objects.filter(reports__in=s_reports)

    return render(request, "dashboards/closters_report.html", {
        'years': years,
        'ter_admins': ter_admins,
        'closters': closters,
        'ed_levels': ed_levels,
        's_reports': s_reports,
        'sections': sections,
        'schools': schools
    })