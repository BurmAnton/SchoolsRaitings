from decimal import Decimal
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.db.models import Sum, Max

from dashboards import utils
from reports.models import Answer, Report, SchoolReport, Section, Field, SectionSreport
from reports.utils import count_section_points
from schools.models import SchoolCloster, School, TerAdmin

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
    # Get all unique years from Report
    years = Report.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    filter = {}
    schools = School.objects.filter(ter_admin__in=ter_admins)

    if request.method != 'POST':
        try:
            year = years[0]
        except:
            year = 2024
        reports = Report.objects.filter(year=year)
    else:
        year = int(request.POST["year"])
        reports = Report.objects.filter(year=year)  
        ter_admins_f = request.POST["ter_admin"]
        if ter_admins_f != '':
            schools = schools.filter(ter_admin=ter_admins_f)
        filter['ter_admin'] = ter_admins_f
        closters_f = request.POST.getlist("closters")
        if len(closters_f) != 0:
            schools = schools.filter(closter__in=closters_f)
            filter['closters'] = closters_f
        ed_levels_f = request.POST.getlist("ed_levels")
        if len(ed_levels_f) != 0:
            schools = schools.filter(ed_level__in=ed_levels_f)
            filter['ed_levels'] = ed_levels_f
        if 'download' in request.POST:
            schools_reports = SchoolReport.objects.filter(report__in=reports, school__in=schools, status='D')
            return utils.generate_ter_admins_report_csv(year, schools, schools_reports)

    schools_reports = SchoolReport.objects.filter(
        report__in=reports,
        school__in=schools,
        status='D'
    ).select_related(
        'school',
        'report',
        'school__ter_admin',
    ).prefetch_related(
        'answers',
        'sections__section__fields',
        'sections__section',
    )

    school_reports_data = {}
    fields_data = {}
    sections = Section.objects.filter(report__in=reports).distinct('number').order_by('number').prefetch_related('fields')

    for s_report in schools_reports:
        school_reports_data[s_report.id] = {
            'green_zone_answers': 0,
            'yellow_zone_answers': 0,
            'red_zone_answers': 0,
            'answers': 0
        }
        # s_report.sections.all().delete()
        # for section in sections:
        #     try:
        #         section_obj = Section.objects.filter(number=section.number, report=s_report.report).first()
        #         if section_obj:
        #             section_sreport, created = SectionSreport.objects.get_or_create(s_report=s_report, section=section_obj)
        #             section_sreport.points = Answer.objects.filter(question__in=section_obj.fields.all(), s_report=s_report).aggregate(Sum('points'))['points__sum'] or 0
        #             section_sreport.zone = count_section_points(s_report, section_sreport.section)
        #             section_sreport.save()
        #     except:
        #         pass
        
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
    sections = Section.objects.filter(report__in=reports).distinct()
    # fields = Field.objects.filter(sections__in=sections).distinct('number').prefetch_related('answers')
    for key, section in sections_data.items():
        for field in section['fields']:
            fields_sum_data[field.id] = field.answers.filter(s_report__in=schools_reports).aggregate(Sum('points'))['points__sum'] or 0

    return render(request, "dashboards/ter_admins_dash.html", {
        "years": years,
        "selected_year": year,
        "reports": reports,   
        "filter": filter,
        'ter_admins': ter_admins,
        'closters': closters,
        'ed_levels': ed_levels,
        'schools_reports': schools_reports,
        'sections': sections,
        'stats': stats,
        'overall_stats': overall_stats,
        'school_reports_data': school_reports_data,
        'fields_data': fields_data,
        'sections_data': sections_data,
        'fields_sum_data': fields_sum_data
    })


@login_required
@csrf_exempt
def school_report(request):
    ter_admins = TerAdmin.objects.filter(representatives=request.user).prefetch_related('schools')
    if not ter_admins.first():
        ter_admins = TerAdmin.objects.all().prefetch_related('schools')
    years = Report.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    school = None
    s_reports = None
    sections = None
    section_data = {}
    stats = {}
    filter = {}

    if request.method == 'POST':
        school = School.objects.get(id=request.POST["school"])
        f_years = request.POST.getlist("years")
        reports = Report.objects.filter(year__in=f_years)
        sections = Section.objects.filter(report__in=reports).distinct('number').order_by('number')
        s_reports = SchoolReport.objects.filter(report__in=reports, school=school, status='D').order_by('report__year').prefetch_related('answers', 'sections')
        
        filter = {
            'years': f_years,
            'school': str(school.id),
            'ter_admin': str(school.ter_admin.id)
        }
        stats, section_data = utils.calculate_stats_and_section_data(f_years, reports, sections, s_reports)

    fields_sum_data = {}
    sections = Section.objects.filter(report__in=reports).distinct()
    fields = Field.objects.filter(sections__in=sections).distinct('number').prefetch_related('answers')
    for field in fields:
        fields_sum_data[field.id] = field.answers.aggregate(Sum('points'))['points__sum'] or 0

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
    
    ter_admins = TerAdmin.objects.filter(representatives=request.user)
    if not ter_admins.first():
        ter_admins = TerAdmin.objects.all()
    years = Report.objects.values_list('year', flat=True).distinct().order_by('-year')
    closters = SchoolCloster.objects.all()
    ed_levels = {
        'A': "1 — 11 классы",
        'M': "1 — 9 классы",
        'S': "1 — 4 классы",
        'MG': "5 — 11 классы",
        'G': "10 — 11 классы",
    }
    
    schools = School.objects.filter(ter_admin__in=ter_admins)
    s_reports = SchoolReport.objects.filter(report__year=year, status='D')
    filter = {}
    
    if request.method != 'POST':
        try:
            year = years[0]
        except:
            year = 2024
        reports = Report.objects.filter(year=year)
        schools = schools.filter(ter_admin=TerAdmin.objects.first())
    elif 'download' in request.POST:
        try:
            year = years[0]
        except:
            year = 2024
        return utils.generate_closters_report_csv( year, schools, s_reports)
    else:
        year = int(request.POST["year"])
        reports = Report.objects.filter(year=year)  
        ter_admin_f = request.POST["ter_admin"]
        if ter_admin_f != '':
            ter_admin = TerAdmin.objects.get(id=ter_admin_f)
            schools = schools.filter(ter_admin=ter_admin)
        filter['ter_admin'] = ter_admin_f
        closters_f = request.POST.getlist("closters")
        if len(closters_f) != 0:
            schools = schools.filter(closter__in=closters_f)
            filter['closters'] = closters_f
        ed_levels_f = request.POST.getlist("ed_levels")
        if len(ed_levels_f) != 0:
            schools = schools.filter(ed_level__in=ed_levels_f)
            filter['ed_levels'] = ed_levels_f
    s_reports = s_reports.filter(school__in=schools)
    
    sections = Section.objects.filter(report__year=year).values('number', 'name').distinct().order_by('number')
    sections_list = []
    for section in sections:
        sections = Section.objects.filter(name=section['name'], report__year=year)
        sections_list.append([section['number'], section['name'], Field.objects.filter(sections__in=sections).distinct().prefetch_related('answers')])

    
    return render(request, "dashboards/closters_report.html", {
        'years': years,
        'ter_admins': ter_admins,
        'closters': closters,
        'ed_levels': ed_levels,
        's_reports': s_reports,
        'sections': sections_list,
        'schools': schools,
        'filter': filter
    })