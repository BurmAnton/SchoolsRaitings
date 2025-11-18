import os
import json
from django import template
from django.db.models import Max, Sum, Case, When, IntegerField, Count, Q

from reports.models import Field, ReportFile, Section, Answer

register = template.Library()


@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(key)
    except:
        return '-'


@register.filter
def get_sorted_fields(section):
    # Если передан SectionSreport, получаем связанную Section
    if hasattr(section, 'section'):
        actual_section = section.section
    else:
        actual_section = section
        
    return sorted(actual_section.fields.all(), key=lambda x: [int(n) for n in str(x.number).split('.')])


@register.filter
def dictsort_fields(sections):
    if not sections:
        return []
    
    # If sections is a queryset, we can use it directly
    if hasattr(sections, 'model'):
        return sorted(sections, key=lambda x: [int(n) for n in str(x.number).split('.')])
    
    # If sections is a single section object
    if hasattr(sections, 'name'):
        related_sections = Section.objects.filter(name=sections.name)
        return sorted(related_sections, key=lambda x: [int(n) for n in str(x.number).split('.')])
    
    return sections  # Return as-is if we can't sort it


@register.filter
def get_answer(answers, question):
    """Возвращает цвет зоны ответа, сопоставляя вопрос по названию."""
    try:
        if not answers.exists():
            return 'white'
        
        first_answer = answers.first()
        if first_answer and first_answer.s_report.report.is_counting == False:
            return 'white'
        
        # Сопоставляем вопрос по названию, а не по ID
        answer = answers.filter(question__name=question.name).first()
        if not answer:
            return 'white'
        
        if answer.zone == "R":
            return "red"
        if answer.zone == "Y":
            return "#ffc600"
        return "green"
    except Exception as e:
        print(f"Error in get_answer: {e}")
        return 'white'

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
        elif question.answer_type == 'MULT':
            # Для множественного выбора возвращаем список ID выбранных опций
            try: 
                return list(answers.get(question=question).selected_options.all().values_list('id', flat=True))
            except: 
                return []
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
    if points is None:
        return "0"
    try:
        points = float(str(points).replace(',', '.'))
        if points % 1 == 0:
            return int(points)
        return str(points)
    except (ValueError, TypeError):
        return "0"


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

    answers = answers.filter(question=field)
    points = answers.aggregate(Sum('points'))['points__sum']

    if points < field.yellow_zone_min:
        return "red"
    if points >= field.green_zone_min:
        return "green"
    return "#ffc600"


@register.filter
def get_section_color(s_report, section):
    from reports.models import Answer, Field

    # Если передан SectionSreport, получаем связанную Section
    if hasattr(section, 'section'):
        actual_section = section.section
    else:
        actual_section = section

    questions = actual_section.fields.all()

    points__sum = Answer.objects.filter(question__in=questions, s_report=s_report).aggregate(Sum('points'))['points__sum']
    if s_report.report.is_counting == False:
        return 'white'
    try:
        if points__sum < actual_section.yellow_zone_min:
            return "red"
        elif points__sum >= actual_section.green_zone_min:
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
        elif question.answer_type == 'MULT':
            # Для множественного выбора возвращаем сумму баллов
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
        elif question.answer_type == 'MULT':
            # Для множественного выбора проверяем наличие максимального значения
            if question.max_points is not None:
                return format_point(question.max_points)
            else:
                # Если максимальные баллы не указаны, возвращаем сумму всех опций
                return format_point(question.options.aggregate(Sum('points'))['points__sum'] or 0)
    except: return 0


@register.filter
def get_file_link(answers, question):
    answer = answers.get(question=question)
    try:
        return answer.file.url
    except:
        return None
    

@register.filter
def get_files(answers, question):
    try:    
        answer = answers.get(question=question)
        return answer.files.all()
    except:
        return []


@register.filter
def get_links(answers, question):
    try:
        answer = answers.get(question=question)
        return answer.links.all()
    except:
        return []


@register.filter 
def get_link(answers, question): 
    try: 
        answer = answers.get(question=question) 
        if answer.link is not None: 
            return answer.link 
        return "" 
    except: 
        return ""


@register.filter
def filename(value):
    try:
        return os.path.basename(value.file.name)
    except:
        return ""

@register.filter
def find_answer_options(answers, question):
    """Возвращает выбранные опции для множественного выбора"""
    try:
        if question.answer_type == 'MULT':
            return answers.get(question=question).selected_options.all()
    except: 
        return []

@register.filter
def index(sequence, position):
    """
    Получает элемент по индексу из списка или другого итерируемого объекта
    """
    try:
        return sequence[position]
    except (IndexError, TypeError):
        return ""

@register.filter
def to_json(value):
    """
    Конвертирует словарь или другой объект в JSON строку
    """
    return json.dumps(value)

@register.filter
def safe_json(value):
    """
    Конвертирует словарь или другой объект в JSON строку, безопасную для использования в JavaScript
    Предотвращает XSS-атаки
    """
    # Заменяем потенциально опасные символы
    json_str = json.dumps(value, ensure_ascii=False)
    return json_str.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

@register.filter
def get_completion_percent(report):
    """Calculates the completion percentage of a report (все типы полей)"""
    try:
        # Получаем все вопросы всех типов
        valid_types = ['LST', 'NMBR', 'PRC', 'BL', 'MULT']
        questions = report.report.sections.all().values_list("fields", flat=True).distinct()
        from reports.models import Field
        valid_questions = Field.objects.filter(id__in=questions, answer_type__in=valid_types)
        total_fields = valid_questions.count()
        if total_fields == 0:
            return 100, "100%"
        
        # Подсчитываем заполненные поля
        filled_count = 0
        for answer in report.answers.filter(question__in=valid_questions):
            if answer.question.answer_type == 'LST' and answer.option is not None:
                filled_count += 1
            elif answer.question.answer_type in ['NMBR', 'PRC'] and answer.number_value is not None:
                filled_count += 1
            elif answer.question.answer_type == 'BL':
                # Бинарные поля всегда считаются заполненными (имеют значение True/False)
                filled_count += 1
            elif answer.question.answer_type == 'MULT' and answer.selected_options.exists():
                filled_count += 1
        
        percentage = int((filled_count / total_fields) * 100)
        return percentage, f"{percentage}%"
    except Exception as e:
        return 0, "0%"

@register.filter
def get_completion_percent_str(report):
    """Returns the string representation of the completion percentage"""
    try:
        percentage, percentage_str = get_completion_percent(report)
        return percentage_str
    except:
        return "0%"

@register.filter
def get_answer_obj(answers, field):
    """Получить объект ответа по полю"""
    return answers.filter(question=field).first()

@register.filter
def get_check_percentage(s_report):
    """Возвращает процент проверенных показателей с оптимизированным запросом"""
    try:
        # Используем агрегацию для подсчета проверенных ответов
        checked_count = s_report.answers.filter(is_checked=True).count()
        
        total_answers = s_report.answers.count()
        if total_answers == 0:
            return 0
            
        return int((checked_count / total_answers) * 100)
    except Exception:
        return 0

@register.filter
def report_zone(school_report):
    """Returns CSS class for displaying report zone color"""
    try:
        if school_report.zone == 'G':
            return 'green'
        elif school_report.zone == 'Y':
            return 'yellow'
        elif school_report.zone == 'R':
            return 'red'
        else:
            return ''
    except:
        return ''

@register.simple_tag(takes_context=True)
def can_edit_field(context, answers, field):
    """
    Проверяет, может ли пользователь редактировать поле.
    Возвращает False, если поле проверено другим пользователем.
    """
    try:
        user = context['request'].user
        answer = answers.filter(question=field).first()
        if not answer:
            return True
            
        # Если поле не проверено, можно редактировать
        if not answer.is_checked:
            return True
            
        # Если поле проверено текущим пользователем, можно редактировать
        if user and answer.checked_by == user:
            return True
            
        # Суперпользователю можно всё
        if user and user.is_superuser:
            return True
            
        # Если поле проверено другим пользователем, нельзя редактировать
        return False
    except:
        return True

@register.filter
def get_check_status_message(answers, field):
    """
    Возвращает сообщение о статусе проверки поля
    """
    try:
        answer = answers.filter(question=field).first()
        if not answer or not answer.is_checked:
            return ""
            
        checked_by = answer.checked_by.get_full_name() if answer.checked_by else "Неизвестно"
        checked_at = answer.checked_at.strftime("%d.%m.%Y %H:%M") if answer.checked_at else ""
        
        return f"Проверено: {checked_by} ({checked_at})"
    except:
        return ""