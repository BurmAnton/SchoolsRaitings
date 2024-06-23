from django import template


register = template.Library()


@register.filter
def find_answer(answers, question):
    if question.answer_type == 'LST':
        try: return answers.get(question=question).option.id
        except: return None
    elif question.answer_type == 'BL':
        return answers.get(question=question).bool_value
    

@register.filter
def get_points(answers, question):
    answer = answers.get(question=question)
    if question.answer_type == 'LST':
        if answer.option is not None:
            if answer.option.points % 1 == 0:
                return int(answer.option.points)
            return str(answer.option.points).replace(',', '.')
    elif question.answer_type == 'BL':
        if answer.bool_value:
            if question.bool_points % 1 == 0:
                return int(question.bool_points)
            return str(question.bool_points).replace(',', '.')
    return 0
