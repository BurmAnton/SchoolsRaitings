from django import template
from django.db.models import Sum

from reports.models import Answer, Field, Question

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_color(zone):
    if zone.zone == "R":
        return "red"
    if zone.zone == "Y":
        return "#ffc600"
    return "green"

@register.filter
def format_point(points):
    if points is None:
        return "—"
    if points % 1 == 0:
        return int(points)
    return str(points).replace(',', '.')


@register.filter
def get_section_points(s_report, section):
    fields = Field.objects.filter(section=section)
    questions = Question.objects.filter(field__in=fields)
    points = s_report.answers.filter(question__in=questions).aggregate(points_sum=Sum('points'))['points_sum']

    return format_point(points)


@register.filter
def get_point_sum(s_reports):
    points = s_reports.aggregate(points_sum=Sum('points'))['points_sum']
    
    return format_point(points)


@register.filter
def get_point_sum_section(s_reports, section):
    fields = Field.objects.filter(section=section)
    questions = Question.objects.filter(field__in=fields)
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