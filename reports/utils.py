from django.urls import reverse
from django.db.models import Sum, Max
import logging

from schools.models import School, SchoolCloster
from users.models import Notification

logger = logging.getLogger(__name__)


def select_range_option(options, value):
    # Вернуть None, если само значение отсутствует или некорректно
    try:
        value = round(float(value), 1)
    except (TypeError, ValueError):
        return None

    # Перебираем все диапазоны и пытаемся найти подходящий
    for option in options:
        range_type = option.range_type
        try:
            if range_type == 'L':
                if option.less_or_equal is not None and value <= round(float(option.less_or_equal), 1):
                    return option
            elif range_type == 'G':
                if option.greater_or_equal is not None and value >= round(float(option.greater_or_equal), 1):
                    return option
            elif range_type == 'D':
                if (
                    option.greater_or_equal is not None and 
                    option.less_or_equal is not None and
                    round(float(option.greater_or_equal), 1) <= value <= round(float(option.less_or_equal), 1)
                ):
                    return option
            elif range_type == 'E':
                if option.equal is not None and value == round(float(option.equal), 1):
                    return option
        except (TypeError, ValueError):
            # Пропускаем некорректно заполненные диапазоны
            continue

    return None


def create_report_notifications(report):
    closter = report.closter
    schools = School.objects.filter(closter=closter, is_archived=False)

    for school in schools:
        if school.principal is not None:
            Notification.objects.create(
                user=school.principal,
                message=f'Вам доступен новый отчёт "{report.name}"',
                link=reverse("report", kwargs={'report_id': report.id, 'school_id': school.id})
            )


def count_report_points(report):
    from reports.models import Field
    for section in report.sections.all():
        points = section.fields.all().aggregate(Sum('points'))['points__sum']
        if points is None: points = 0

        if section.points != points:
            section.points = points
            section.save()
    feilds = Field.objects.filter(sections__in=report.sections.all())
    points = feilds.aggregate(Sum('points'))['points__sum']
    return points


def count_points(s_report):
    """Count total points and determine zone for a school report"""
    try:
        from reports.models import Answer  # Move import inside function
        points_sum = Answer.objects.filter(s_report=s_report).aggregate(Sum('points'))['points__sum'] or 0
        points_sum = round(points_sum, 1)
        
        if s_report.report.is_counting == False:
            return 'W', points_sum
            
        if points_sum < s_report.report.yellow_zone_min:
            return 'R', points_sum
        elif points_sum >= s_report.report.green_zone_min:
            return 'G', points_sum
        else:
            return 'Y', points_sum
    except:
        return 'R', 0


def count_points_field(s_report, field):
    from reports.models import Answer
    
    points__sum = Answer.objects.filter(question=field, s_report=s_report).aggregate(Sum('points'))['points__sum'] or 0
    if s_report.report.is_counting == False:
        return 'W'
    
    # Проверяем, заданы ли минимальные значения для жёлтой и зелёной зон в показателе
    if field.yellow_zone_min is not None and field.green_zone_min is not None:
        if points__sum < field.yellow_zone_min:
            return "R"
        elif points__sum >= field.green_zone_min:
            return "G"
        return "Y"
    # Если в показателе нет значений, используем значения из родительского раздела
    else:
        try:
            # Получаем раздел, к которому относится поле
            section = field.sections.first()
            if section and section.yellow_zone_min is not None and section.green_zone_min is not None:
                if points__sum < section.yellow_zone_min:
                    return "R"
                elif points__sum >= section.green_zone_min:
                    return "G"
                return "Y"
        except: 
            pass
    
    # Если ни в показателе, ни в разделе не заданы значения, возвращаем красную зону
    return 'R'


def count_section_points(s_report, section):
    from reports.models import Answer

    points__sum = Answer.objects.filter(question__in=section.fields.all(), s_report=s_report).aggregate(Sum('points'))['points__sum']
    if s_report.report.is_counting == False:
        return 'W'
    
    try:
        if points__sum < section.yellow_zone_min:
            return "R"
        elif points__sum >= section.green_zone_min:
            return "G"
        return "Y"
    except: return 'R'


def count_answers_points(answers):
    """Count points for answers"""
    from reports.models import Answer
    
    for answer in answers:
        field = answer.question
        if field.answer_type == 'LST':
            if answer.option is not None:
                answer.points = answer.option.points
                answer.zone = answer.option.zone
        elif field.answer_type == 'BL':
            answer.points = field.bool_points if answer.bool_value else 0
            answer.zone = "G" if answer.bool_value else "R"
        elif field.answer_type in ['NMBR', 'PRC']:
            r_option = select_range_option(field.range_options.all(), answer.number_value)
            if r_option == None: 
                answer.points = 0
                answer.zone = "R"
            else: 
                answer.points = r_option.points
                answer.zone = r_option.zone
        answer.save()  # This will trigger the signal to update SectionSreport


def update_section_sreports(s_report):
    """
    Updates or creates SectionSreport objects for a given SchoolReport
    """
    from reports.models import Section, SectionSreport, Answer
    
    sections = Section.objects.filter(report=s_report.report).distinct('number').order_by('number')
    
    for section in sections:
        try:
            section_obj = Section.objects.filter(
                number=section.number, 
                report=s_report.report
            ).first()
            
            if section_obj:
                section_sreport, created = SectionSreport.objects.get_or_create(
                    s_report=s_report, 
                    section=section_obj
                )
                section_sreport.points = (
                    Answer.objects.filter(
                        question__in=section_obj.fields.all(), 
                        s_report=s_report
                    ).aggregate(Sum('points'))['points__sum'] or 0
                )
                section_sreport.zone = count_section_points(s_report, section_sreport.section)
                section_sreport.save()
        except Exception as e:
            logger.error(f"Error updating section report for section {section.number}: {str(e)}")


