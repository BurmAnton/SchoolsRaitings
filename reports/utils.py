from django.urls import reverse
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
