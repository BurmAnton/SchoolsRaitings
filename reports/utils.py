from django.urls import reverse
from django.db.models import Sum, Max

from schools.models import School, SchoolCloster
from users.models import Notification


def select_range_option(options, value):
    for option in options:
        value = round(value, 1)
        match option.range_type:
            case 'L':
                if value <= round(float(option.less_or_equal), 1): return option
            case 'G':
                if value >= round(float(option.greater_or_equal), 1): return option
            case 'D':
                if round(float(option.greater_or_equal), 1) <= value <= round(float(option.less_or_equal), 1): 
                    return option
            case 'E':
                if value == round(float(option.equal), 1): return option

    return None


def create_report_notifications(report):
    closter = report.closter
    schools = School.objects.filter(closter=closter)

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
    from reports.models import Answer

    report = s_report.report
    points_sum = round(Answer.objects.filter( s_report=s_report).aggregate(Sum('points'))['points__sum'], 1)
    if report.is_counting == False:
        return 'W', points_sum
    
    if points_sum < report.yellow_zone_min:
        report_zone = 'R'
    elif points_sum >= report.green_zone_min:
        report_zone = 'G'
    else:
        report_zone = 'Y'

    return report_zone, points_sum


def count_points_field(s_report, field):
    from reports.models import Answer
    
    points__sum = Answer.objects.filter(question__in=field.questions.all(), s_report=s_report).aggregate(Sum('points'))['points__sum']
    if s_report.report.is_counting == False:
        return 'W'
    try:
        if points__sum < field.yellow_zone_min:
            return "R"
        elif points__sum >= field.green_zone_min:
            return "G"
        return "Y"
    except: return 'R'


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
        answer.save()


