from django import template
from django.db.models import Sum, Max, Avg

from reports.models import Answer, Field, Section
from dashboards import utils
from schools.models import TerAdmin

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_color(zone):
    if zone == "R":
        return "red"
    if zone == "Y":
        return "#ffc600"
    return "green"

@register.filter
def get_section_colord(s_report, section):
    sections = Section.objects.filter(name=section.name, report=s_report.report)
    if sections.count() > 0:
        questions = sections[0].fields.all()
    else:
        return 'white'

    points__sum = Answer.objects.filter(question__in=questions, s_report=s_report).aggregate(Sum('points'))['points__sum']
    if points__sum is None:
        return 'white'
    if s_report.report.is_counting == False:
        return 'white'
    try:
        if points__sum < section.yellow_zone_min:
            return "red"
        elif points__sum >= section.green_zone_min:
            return "green"
        return "#ffc600"
    except: return 'red'


@register.filter        
def get_section_color_by_name(s_report, section_name):
    sections = Section.objects.filter(name=section_name, report=s_report.report)
    if sections.count() > 0:
        questions = sections[0].fields.all()
    else:
        return 'white'
    section = sections[0]
    points__sum = Answer.objects.filter(question__in=questions, s_report=s_report).aggregate(Sum('points'))['points__sum']
    if points__sum is None:
        return 'white'
    if s_report.report.is_counting == False:
        return 'white'
    try:
        if points__sum < section.yellow_zone_min:
            return "red"
        elif points__sum >= section.green_zone_min: 
            return "green"
        return "#ffc600"
    except: return 'red'


@register.filter
def format_point(points):
    if points is None:
        return "0"
    if points % 1 == 0:
        return int(points)
    return str(points).replace(',', '.')


@register.filter
def get_section_points(s_report, section):
    sections = Section.objects.filter(name=section.name, report=s_report.report)
    if sections.count() > 0:
        questions = sections[0].fields.all()
    else:
        return "-"

    points__sum = Answer.objects.filter(question__in=questions, s_report=s_report).aggregate(Sum('points'))['points__sum']
    return format_point(points__sum)


@register.filter
def get_section_points_by_name(s_report, section_name):
    sections = Section.objects.filter(name=section_name, report=s_report.report)
    if sections.count() > 0:
        questions = sections[0].fields.all()
    else:
        return "-"

    points__sum = Answer.objects.filter(question__in=questions, s_report=s_report).aggregate(Sum('points'))['points__sum']
    return format_point(points__sum)


@register.filter
def get_point_sum(s_reports):
    points = s_reports.aggregate(points_sum=Sum('points'))['points_sum']
    
    return format_point(points)

@register.filter
def get_color_field_dash(answers, field):
    answers = answers.filter(question__in=field.questions.all())
    points = answers.aggregate(Sum('points'))['points__sum']

    if points < field.yellow_zone_min:
        return "red"
    if points >= field.green_zone_min:
        return "green"
    return "#ffc600" 


@register.filter
def get_point_sum_section(s_reports, section):
    questions = section.fields.all()
    points = Answer.objects.filter(question__in=questions, s_report__in=s_reports).aggregate(points_sum=Sum('points'))['points_sum']

    if points is None:
        return "0"
    return format_point(points)


@register.filter
def get_field_points(s_report, field):
    answer = Answer.objects.filter(s_report=s_report, question=field)

    if answer.count() == 0:
        return "-"
    points = s_report.answers.filter(question=field).aggregate(points_sum=Sum('points'))['points_sum']
    if points is None:
        return "-"
    return format_point(points)

@register.filter
def get_point_sum_field(s_reports, field):

    answers = Answer.objects.filter(s_report__in=s_reports, question=field)
    points = answers.filter(question=field).aggregate(points_sum=Sum('points'))['points_sum']

    return format_point(points)

@register.filter
def get_year_points(s_reports, year):
    points = s_reports.filter(report__year=str(year)).aggregate(points_sum=Sum('points'))['points_sum']
    return format_point(points)

@register.filter
def max_value(questions, s_reports):
    max_points = 0
    for s_report in s_reports:
        points = Answer.objects.filter(question__in=questions, s_report=s_report).aggregate(points_sum=Sum('points'))['points_sum'] or 0
        max_points = max(max_points, points)
    return format_point(max_points)



@register.filter
def avg_value(questions, s_reports):
    total_points = 0
    count = 0
    for s_report in s_reports:
        points = Answer.objects.filter(question__in=questions, s_report=s_report).aggregate(points_sum=Sum('points'))['points_sum'] or 0
        total_points += points
        count += 1
    
    if count == 0:
        return "0.00"
    
    avg_points = total_points / count
    rounded_avg = round(avg_points, 1)
    return format_point(rounded_avg)


@register.filter
def max_value_section(question, s_reports):
    max_points = Answer.objects.filter(question=question, s_report__in=s_reports).aggregate(points_sum=Max('points'))['points_sum'] or 0

    return format_point(max_points)



@register.filter
def avg_value_section(question, s_reports):
    avg_points = Answer.objects.filter(question=question, s_report__in=s_reports).aggregate(points_sum=Avg('points'))['points_sum'] or 0

    rounded_avg = round(avg_points, 1)
    return format_point(rounded_avg)


@register.filter
def get_school_report_chart(categories, section_data):
    return utils.generate_school_report_chart(section_data, categories)


@register.filter
def count_zone_answers(answers, zone):
    return answers.filter(zone=zone).count()

@register.filter
def count_zone_answers_percent(answers, zone):
    return f'{answers.filter(zone=zone).count() / answers.count() * 100:.1f}%'


@register.filter
def green_zone_count(s_reports, field):
    return f'{s_reports.filter(answers__zone="G", answers__question=field).count()} ({s_reports.filter(answers__zone="G", answers__question=field).count() / s_reports.count() * 100:.1f}%)'

@register.filter
def yellow_zone_count(s_reports, field):
    return f'{s_reports.filter(answers__zone="Y", answers__question=field).count()} ({s_reports.filter(answers__zone="Y", answers__question=field).count() / s_reports.count() * 100:.1f}%)'

@register.filter
def red_zone_count(s_reports, field):
    return f'{s_reports.filter(answers__zone="R", answers__question=field).count()} ({s_reports.filter(answers__zone="R", answers__question=field).count() / s_reports.count() * 100:.1f}%)'    

@register.filter
def is_ter_admin_exist(user):
    ter_admin = TerAdmin.objects.filter(representatives=user)
    return ter_admin.count() != 0
