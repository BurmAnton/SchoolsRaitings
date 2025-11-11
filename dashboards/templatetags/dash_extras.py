from django import template
from django.db.models import Sum, Max, Avg

from reports.models import Answer, Field, Section, SectionSreport
from dashboards import utils
from schools.models import TerAdmin

register = template.Library()


@register.filter
def get_item(dictionary, key):
    try:    
        return dictionary.get(key)
    except:
        return '-'


@register.filter
def get_field_value(sreport_fields, field):
    try:
        return sreport_fields['fields'][field.number]['points']
    except (TypeError, KeyError):
        return "-"
    

@register.filter
def get_field_zone(sreport_fields, field):
    try:
        zone = sreport_fields['fields'][field.number]['zone']
        if zone == "R":
            return "red"
        if zone == "Y":
            return "#ffc600"
        if zone == "G":
            return "green"
        return "white"
    except (TypeError, KeyError):
        return "-"

@register.filter
def dictsort_fields_dash(fields):
    return sorted(fields, key=lambda x: [int(n) for n in str(x.number).split('.')])


@register.filter
def get_gzone_answers_percent(school_reports_data, sreport_id):
    g_count = school_reports_data[sreport_id]['green_zone_answers']
    question_count = school_reports_data[sreport_id]['answers']
    try:
        return f'{g_count / question_count * 100:.1f}%'
    except:
        return '0.0%'


@register.filter
def get_yzone_answers_percent(school_reports_data, sreport_id):
    g_count = school_reports_data[sreport_id]['yellow_zone_answers']
    question_count = school_reports_data[sreport_id]['answers']
    try:
        return f'{g_count / question_count * 100:.1f}%'
    except:
        return '0.0%'


@register.filter
def get_rzone_answers_percent(school_reports_data, sreport_id):
    g_count = school_reports_data[sreport_id]['red_zone_answers']
    question_count = school_reports_data[sreport_id]['answers']
    try:
        return f'{g_count / question_count * 100:.1f}%'
    except:
        return '0.0%'


@register.filter
def get_color(zone):
    if zone == "R":
        return "red"
    if zone == "Y":
        return "#ffc600"
    if zone == "G":
        return "green"
    return "white"

@register.filter
def get_answer_color_by_field(s_report, field):
    """Возвращает цвет зоны ответа по показателю, используя кеш на s_report.
    Сопоставление выполняется по названию показателя, чтобы корректно работать при копировании.
    """
    try:
        if not s_report or not field:
            return 'white'
        # Если отчёт не считается, не подсвечиваем
        if hasattr(s_report, 'report') and getattr(s_report.report, 'is_counting', True) is False:
            return 'white'

        # Кешируем словарь названий показателей -> зона
        zone_map = getattr(s_report, '_answers_zone_by_name', None)
        if zone_map is None:
            zone_map = {}
            # Важно: answers должны быть предзагружены с question (select_related)
            for a in s_report.answers.all():
                if a.question:
                    zone_map[a.question.name] = a.zone
            setattr(s_report, '_answers_zone_by_name', zone_map)

        zone = zone_map.get(field.name)
        if not zone:
            return 'white'
        return get_color(zone)
    except Exception as e:
        print(f"Error in get_answer_color_by_field: {e}")
        return 'white'

@register.filter
def get_section_colord(s_report, section):
    """Определяет цвет зоны по баллам раздела, сопоставляя по названию."""
    try:
        if not s_report or not section:
            return 'white'
        
        # Сопоставляем раздел по названию, а не по номеру/ID
        section_in_report = Section.objects.filter(name=section.name, report=s_report.report).first()
      
        if not section_in_report:
            return 'white'
        
        section_report = SectionSreport.objects.filter(
            s_report=s_report,
            section=section_in_report 
        ).first()
        
        if not section_report:
            # Calculate points for this section
            questions = section_in_report.fields.all()
            points = Answer.objects.filter(
                question__in=questions,
                s_report=s_report
            ).aggregate(Sum('points'))['points__sum'] or 0
            
            # Create new section report
            section_report = SectionSreport.objects.create(
                s_report=s_report,
                section=section_in_report,
                points=points
            )

        if not section_report or section_report.points is None:
            return 'white'
            
        if not s_report.report.is_counting:
            return 'white'
            
        if section_report.points < section_in_report.yellow_zone_min:
            return "red"
        elif section_report.points >= section_in_report.green_zone_min:
            return "green"
        return "#ffc600"
    except Exception as e:
        print(f"Error in get_section_colord: {e}")
        return 'white'


@register.filter        
def get_section_color_by_name(s_report, section_name):
    """Определяет цвет зоны по баллам раздела, используя SectionSreport (без JOIN)."""
    try:
        if not s_report or not hasattr(s_report, 'report'):
            return 'white'

        section = Section.objects.filter(name=section_name, report=s_report.report).first()
        if not section:
            return 'white'

        # Быстрый путь через SectionSreport (предзагружено в view)
        section_report = s_report.sections.filter(section=section).first()
        if not section_report or section_report.points is None:
            return 'white'

        if not s_report.report.is_counting:
            return 'white'

        if section_report.points < section.yellow_zone_min:
            return "red"
        elif section_report.points >= section.green_zone_min:
            return "green"
        return "#ffc600"
    except Exception as e:
        print(f"Error in get_section_color_by_name: {e}")
        return 'white'


@register.filter
def format_point(points):
    try:
        if points is None:
            return "0"
        if isinstance(points, (int, float)):
            if points % 1 == 0:
                return int(points)
        return str(points).replace(',', '.')
    except Exception:
        return "0"


@register.filter
def get_section_points(s_report, section):
    """Возвращает баллы по разделу, сопоставляя по названию."""
    try:
        if not s_report or not section:
            return "-"
        
        # Сопоставляем разделы по названию, а не по номеру/ID
        sec_rep = SectionSreport.objects.filter(
            s_report=s_report, 
            section__name=section.name
        ).first()
        
        if sec_rep and sec_rep.points is not None:
            return format_point(sec_rep.points)
        return "-"
    except Exception as e:
        print(f"Error in get_section_points: {e}")
        return "-"



@register.filter
def get_section_points_by_name(s_report, number):
    """Возвращает баллы по разделу через SectionSreport (быстрее одного запроса)."""
    try:
        if not s_report or not number:
            return "-"

        # Пытаемся сразу взять из SectionSreport (это уже предзагружено в view)
        sec_rep = s_report.sections.filter(section__number=number).first()
        if sec_rep:
            # Если баллы None, считаем их равными 0 (чтобы избежать тяжёлого запроса)
            points_val = sec_rep.points if sec_rep.points is not None else 0
            return format_point(points_val)

        # Fallback — считаем через ответы (редко, когда нет SectionSreport)
        sections = Section.objects.filter(number=number, report=s_report.report)
        if not sections.exists():
            return "-"

        questions = sections[0].fields.all()
        if not questions.exists():
            return "-"

        points__sum = Answer.objects.filter(question__in=questions, s_report=s_report).aggregate(Sum('points'))['points__sum']
        return format_point(points__sum)

    except Exception as e:
        print(f"Error in get_section_points_by_name: {e}")
        return "-"


@register.filter
def get_point_sum(s_reports):
    try:
        if not s_reports:
            return "0"
        points = s_reports.aggregate(points_sum=Sum('points'))['points_sum']
        return format_point(points)
    except Exception as e:
        print(f"Error in get_point_sum: {e}")
        return "0"

@register.filter
def get_color_field_dash(answers, field):
    try:
        if not answers or not field:
            return "white"
        answers = answers.filter(question__in=field.questions.all())
        points = answers.aggregate(Sum('points'))['points__sum']
        
        if points is None:
            return "white"

        if points < field.yellow_zone_min:
            return "red"
        if points >= field.green_zone_min:
            return "green"
        return "#ffc600"
    except Exception as e:
        print(f"Error in get_color_field_dash: {e}")
        return "white"


@register.filter
def get_point_sum_section(s_reports, section):
    """Возвращает сумму баллов по разделу, сопоставляя по названию."""
    try:
        if not s_reports or not section:
            return "0"
        # Сопоставляем раздел по названию, а не по номеру/ID
        points = SectionSreport.objects.filter(s_report__in=s_reports, section__name=section.name).aggregate(Sum('points'))['points__sum'] or 0
        return format_point(points)
    except Exception as e:
        print(f"Error in get_point_sum_section: {e}")
        return "0"

@register.filter
def get_field_points(s_report, field):
    """Быстрый доступ к баллам по показателю, сопоставляя по названию показателя."""
    try:
        if not s_report or not field:
            return "-"

        # Создаём и кэшируем словарь answer.question__name -> points при первом обращении
        # Сопоставляем по названию показателя, а не по ID
        answers_map = getattr(s_report, '_answers_map_by_name', None)
        if answers_map is None:
            answers_map = {}
            for a in s_report.answers.select_related('question').all():
                if a.question:
                    # Используем название показателя как ключ
                    answers_map[a.question.name] = a.points
            setattr(s_report, '_answers_map_by_name', answers_map)

        points = answers_map.get(field.name)
        if points is None:
            return "-"
        return format_point(points)
    except Exception as e:
        print(f"Error in get_field_points: {e}")
        return "-"


@register.filter
def get_year_points(s_reports, year):
    try:
        if not s_reports:
            return "0"
        points = s_reports.filter(report__year=str(year)).aggregate(points_sum=Sum('points'))['points_sum']
        return format_point(points)
    except Exception as e:
        print(f"Error in get_year_points: {e}")
        return "0"

@register.filter
def max_value(questions, s_reports):
    """Возвращает максимальное значение баллов по конкретному разделу среди списка отчётов."""
    try:
        if not questions or not s_reports:
            return "0"

        first_q = next(iter(questions), None)
        if not first_q:
            return "0"

        # Извлекаем номер раздела (предполагаем, что все вопросы относятся к одному разделу)
        sec = first_q.sections.first() if hasattr(first_q, 'sections') else None
        sec_number = sec.number if sec else None
        if not sec_number:
            return "0"

        max_points = SectionSreport.objects.filter(
            s_report__in=s_reports,
            section__number=sec_number
        ).aggregate(Max('points'))['points__max'] or 0

        return format_point(max_points)
    except Exception as e:
        print(f"Error in max_value: {e}")
        return "0"



@register.filter
def avg_value(questions, s_reports):
    """Среднее значение баллов по разделу (SectionSreport)."""
    try:
        if not questions or not s_reports:
            return "0.00"

        first_q = next(iter(questions), None)
        if not first_q:
            return "0.00"

        sec = first_q.sections.first() if hasattr(first_q, 'sections') else None
        sec_number = sec.number if sec else None
        if not sec_number:
            return "0.00"

        avg_points = SectionSreport.objects.filter(
            s_report__in=s_reports,
            section__number=sec_number
        ).aggregate(avg_points=Avg('points'))['avg_points'] or 0

        avg_val = round(float(avg_points), 1)
        return format_point(avg_val)
    except Exception as e:
        print(f"Error in avg_value: {e}")
        return "0.00"


@register.filter
def max_value_section(question, s_reports):
    try:
        if not question or not s_reports:
            return "0"
        max_points = Answer.objects.filter(question=question, s_report__in=s_reports).values('points').aggregate(Max('points'))['points__max'] or 0
        return format_point(max_points)
    except Exception as e:
        print(f"Error in max_value_section: {e}")
        return "0"



@register.filter
def avg_value_section(question, s_reports):
    try:
        if not question or not s_reports:
            return "0.00"
        avg_points = Answer.objects.filter(question=question, s_report__in=s_reports).values('points').aggregate(avg_points=Avg('points'))['avg_points'] or 0
        rounded_avg = round(avg_points, 1)
        return format_point(rounded_avg)
    except Exception as e:
        print(f"Error in avg_value_section: {e}")
        return "0.00"


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

@register.filter
def safe_json(value):
    """
    Конвертирует словарь или другой объект в JSON строку, безопасную для использования в JavaScript
    Предотвращает XSS-атаки
    """
    # Заменяем потенциально опасные символы
    import json
    json_str = json.dumps(value, ensure_ascii=False)
    return json_str.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

@register.filter
def multiply(value, arg):
    """
    Умножает значение на аргумент.
    Пример: {{ value|multiply:2 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """
    Divides the value by the argument
    
    Usage:
        {{ value|divide:arg }}
    
    Examples:
        {{ 10|divide:2 }}
        {{ 10|divide:3 }}
        
    Results:
        5
        3.33
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def subtract(value, arg):
    """
    Subtracts the argument from the value
    
    Usage:
        {{ value|subtract:arg }}
    
    Examples:
        {{ 10|subtract:2 }}
        {{ 5|subtract:7 }}
        
    Results:
        8
        -2
    """
    try:
        return float(value) - float(arg)
    except ValueError:
        return 0

@register.filter
def get_report_by_year(s_reports, year):
    """
    Возвращает SchoolReport за указанный год из списка s_reports, либо None.
    """
    for sr in s_reports:
        if hasattr(sr, 'report') and hasattr(sr.report, 'year'):
            if str(sr.report.year) == str(year) or sr.report.year == year:
                return sr
    return None
