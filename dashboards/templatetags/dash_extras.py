from django import template
from django.db.models import Sum

from reports.models import Answer, Field, Question

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
def get_section_color(s_report, section):
    questions = Question.objects.filter(field__in=section.fields.all())

    points__sum = Answer.objects.filter(question__in=questions, s_report=s_report).aggregate(Sum('points'))['points__sum']
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
        return "—"
    if points % 1 == 0:
        return int(points)
    return str(points).replace(',', '.')


@register.filter
def get_section_points(s_report, section):
    questions = Question.objects.filter(field__in=section.fields.all())

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
    questions = Question.objects.filter(field__in=section.fields.all())
    points = Answer.objects.filter(question__in=questions, s_report__in=s_reports).aggregate(points_sum=Sum('points'))['points_sum']

    if points is None:
        return "—"
    return format_point(points)


@register.filter
def get_field_points(s_report, field):
    points = s_report.answers.filter(question__in=field.questions.all()).aggregate(points_sum=Sum('points'))['points_sum']

    return format_point(points)

@register.filter
def get_point_sum_field(s_reports, field):
    questions = Question.objects.filter(field=field)
    answers = Answer.objects.filter(s_report__in=s_reports, question__in=questions)
    points = answers.filter(question__in=field.questions.all()).aggregate(points_sum=Sum('points'))['points_sum']

    return format_point(points)