from django import template
from django.db.models import Max, Sum

from reports.models import ReportFile

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def get_answer(answers, question):
    if answers[0].s_report.report.is_counting == False:
        return 'white'
    answer = answers.get(question=question)
    if answer.zone == "R":
        return "red"
    if answer.zone == "Y":
        return "#ffc600"
    return "green"


@register.filter
def find_answer(answers, question):
    try:
        if question.answer_type == 'LST':
            try: return answers.get(question=question).option.id
            except: return 0
        elif question.answer_type == 'BL':
            return answers.get(question=question).bool_value
        elif question.answer_type in ['NMBR', 'PRC']:
            return format_point(answers.get(question=question).number_value)
    except: return 0


@register.filter
def is_answer_changed(answers, question):
    try:
        return answers.get(question=question).is_mod_by_ter
    except: return False


@register.filter
def is_answer_changed_by_mo(answers, question):
    try:
        return answers.get(question=question).is_mod_by_mo
    except: return False


@register.filter
def format_point(points):
    if points % 1 == 0:
        return int(points)
    return str(points).replace(',', '.')


@register.filter
def get_color(zone):
    if zone == "R":
        return "red"
    if zone == "Y":
        return "#ffc600"
    return "green"


@register.filter
def get_color_field(answers, field):
    if answers[0].s_report.report.is_counting == False:
        return 'white'
    answers = answers.filter(question__in=field.questions.all())
    points = answers.aggregate(Sum('points'))['points__sum']

    if points < field.yellow_zone_min:
        return "red"
    if points >= field.green_zone_min:
        return "green"
    return "#ffc600"



@register.filter
def get_section_color(s_report, section):
    from reports.models import Answer, Question

    questions = Question.objects.filter(field__in=section.fields.all())

    points__sum = Answer.objects.filter(question__in=questions, s_report=s_report).aggregate(Sum('points'))['points__sum']
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
def get_points(answers, question):
    try:
        answer = answers.get(question=question)
        if question.answer_type == 'LST':
            if answer.option is not None:
                return format_point(answer.option.points)
            return 0
        elif question.answer_type == 'BL':
            if answer.bool_value:
                return format_point(question.bool_points)
            return 0
        elif question.answer_type in ['NMBR', 'PRC']:
            return format_point(answer.points)
    except: return 0


@register.filter
def get_max_points(question):
    try:
        if question.answer_type == 'LST':
            points = question.options.aggregate(Max('points'))['points__max']
            return format_point(points)
        elif question.answer_type == 'BL':
            return format_point(question.bool_points)
        elif question.answer_type in ['NMBR', 'PRC']:
            points = question.range_options.aggregate(Max('points'))['points__max']
            return format_point(points)
    except: return 0


@register.filter
def get_file_link(answers, question):
    answer = answers.get(question=question)
    try:
        return ReportFile.objects.get(answers=answer).file.url
    except:
        return None