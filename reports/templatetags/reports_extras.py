from django import template
from django.db.models import Max

register = template.Library()


@register.filter
def find_answer(answers, question):
    if question.answer_type == 'LST':
        try: return answers.get(question=question).option.id
        except: return None
    elif question.answer_type == 'BL':
        return answers.get(question=question).bool_value
    elif question.answer_type in ['NMBR', 'PRC']:
        return format_point(answers.get(question=question).number_value)
    

def format_point(points):
    if points % 1 == 0:
        return int(points)
    return str(points).replace(',', '.')


@register.filter
def get_points(answers, question):
    answer = answers.get(question=question)
    if question.answer_type == 'LST':
        if answer.option is not None:
            return format_point(answer.option.points)
    elif question.answer_type == 'BL':
        if answer.bool_value:
            return format_point(question.bool_points)
    elif question.answer_type in ['NMBR', 'PRC']:
        return format_point(answer.points)
    return 0


@register.filter
def get_max_points(question):
    if question.answer_type == 'LST':
        points = question.options.aggregate(Max('points'))['points__max']
        return format_point(points)
    elif question.answer_type == 'BL':
        return format_point(question.bool_points)
    elif question.answer_type in ['NMBR', 'PRC']:
        points = question.range_options.aggregate(Max('points'))['points__max']
        return format_point(points)

