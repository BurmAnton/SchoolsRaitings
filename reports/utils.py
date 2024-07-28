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
    closters = SchoolCloster.objects.filter(zones__in=report.zones.all())
    schools = School.objects.filter(closter__in=closters)

    for school in schools:
        if school.principal is not None:
            Notification.objects.create(
                user=school.principal,
                message=f'Вам доступен новый отчёт "{report.name}"',
                link=reverse("report", kwargs={'report_id': report.id, 'school_id': school.id})
            )


def count_report_points(report):
    from reports.models import Option, RangeOption
    points = 0
    for section in report.sections.all():
        for field in section.fields.all():
            for question in field.questions.all():
                match question.answer_type:
                    case 'BL':
                        points += question.bool_points
                    case 'LST':
                        points += Option.objects.filter(question=question).aggregate(Max('points'))['points__max']
                    case _:
                        points += RangeOption.objects.filter(question=question).aggregate(Max('points'))['points__max']
    return points


def count_points(s_report):
    from reports.models import Answer, ReportZone

    points_sum = round(Answer.objects.filter( s_report=s_report).aggregate(Sum('points'))['points__sum'], 1)
    zones = ReportZone.objects.filter(report=s_report.report)
    
    report_zone = None
    for zone in zones:
        match zone.range_type:
            case 'L':
                if points_sum <= round(float(zone.less_or_equal), 1):
                    report_zone = zone
                    break
            case 'G':
                if points_sum >= round(float(zone.greater_or_equal), 1):
                    report_zone = zone
                    break
            case 'D':
                if round(float(zone.greater_or_equal), 1) <= points_sum <= round(float(zone.less_or_equal), 1):
                    report_zone = zone
                    break

    return report_zone, points_sum