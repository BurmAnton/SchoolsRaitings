import os
from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL
from django.db.models.signals import pre_save, post_save, m2m_changed
from django.dispatch import receiver
from django.db.models import Sum, Max

from tinymce import models as tinymce_models

from reports import utils
from reports.utils import count_report_points, create_report_notifications
from reports.utils import count_points as reports_count_points
from users.models import Notification, User
from schools.models import School, SchoolCloster


class Report(models.Model):
    year = models.IntegerField('Год', null=False, blank=False)
    name = models.CharField("Название отчёта", max_length=750)
    closter = models.ForeignKey(
        SchoolCloster,
        verbose_name='Кластер',
        related_name='reports',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    SCHOOL_LEVELS = [
        ('A', "1 — 11 классы"),
        ('M', "1 — 9 классы"),
        ('S', "1 — 4 классы"),
        ('G', "10 — 11 классы"),
        ('MG', "5 — 11 классы"),
    ]
    ed_level = models.CharField(
        "Уровень образования", choices=SCHOOL_LEVELS, max_length=2, blank=False, null=False
    )
    is_published = models.BooleanField(
        "Опубликовать?", default=False
    )

    yellow_zone_min = models.DecimalField(
        "Жёлтая зона (минимум)", max_digits=5,
        decimal_places=1, null=True, blank=True, default=0

    )
    green_zone_min = models.DecimalField(
        "Зеленая зона (минимум)", max_digits=5, decimal_places=1,
        null=True, blank=True, default=0
    )
    is_counting = models.BooleanField(
        "Показывать зоны?", default=False
    )
    points = models.DecimalField(
        "Макс. баллов", max_digits=5,
        decimal_places=1, null=False, blank=False, default=0
    )

    class Meta:
        verbose_name = "Отчёт (шаблон)"
        verbose_name_plural = "Отчёты (шаблон)"

    def __str__(self):
        return  f'{self.name} ({self.year})'


# Signal to calculate points in Report and Section when a Report is modified
@receiver(post_save, sender=Report)
def update_report_points(sender, instance, **kwargs):
    # Recalculate points for the Report instance
    report_points = instance.sections.aggregate(Sum('points'))['points__sum'] or 0
    Report.objects.filter(pk=instance.pk).update(points=report_points)

    school_reports = SchoolReport.objects.filter(report=instance)
    for school_report in school_reports:
        try:
            points_sum = round(Answer.objects.filter( s_report=school_report).aggregate(Sum('points'))['points__sum'], 1)
        except:
            points_sum = 0
        if points_sum < instance.yellow_zone_min:
            report_zone = 'R'
        elif points_sum >= instance.green_zone_min:
            report_zone = 'G'
        else:
            report_zone = 'Y'
        school_report.zone = report_zone
        school_report.save()


@receiver(pre_save, sender=Report, dispatch_uid='report_save_signal')
def create_notification(sender, instance, using, **kwargs):
    if instance.is_published:
        if instance.id is None:
            pass
        elif Report.objects.get(id=instance.id).is_published == False:
            create_report_notifications(instance)


class Attachment(models.Model):
    name = models.CharField("Название вложения", max_length=750)
    ATTACHMENT_TYPES = [
        ('DC', "Документ (прикреплённый файл)"),
        ('LNK', 'Ссылка'),
        ('OTH', 'Иной источник (без ссылки/файла)'),
    ]
    attachment_type = models.CharField(
        "Цель обучения", max_length=3, 
        choices=ATTACHMENT_TYPES, 
        blank=True, null=True
    )

    class Meta:
        verbose_name = "Источник данных"
        verbose_name_plural = "Источники данных"

    def __str__(self):
        return f'{self.name} ({self.get_attachment_type_display()})'


class Section(models.Model):
    number = models.CharField('Номер критерия', null=True, blank=True, max_length=500)
    name = models.CharField("Название критерия", max_length=500)
    report = models.ForeignKey(
        Report,
        verbose_name='отчёт',
        related_name='sections',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    fields = models.ManyToManyField(
        "Field",
        verbose_name="Показатели",
        related_name="sections",
        blank=True
    )

    yellow_zone_min = models.DecimalField(
        "Жёлтая зона (минимум)", max_digits=5,
        decimal_places=1, null=False, blank=False, default=0

    )
    green_zone_min = models.DecimalField(
        "Зеленая зона (минимум)", max_digits=5, decimal_places=1,
        null=False, blank=False, default=0
    )
    points = models.DecimalField(
        "Макс. баллов", max_digits=5,
        decimal_places=1, null=False, blank=False, default=0
    )
    
    note = tinymce_models.HTMLField(
        "Примечание", null=True, blank=True, default=None
    )

    class Meta:
        # ordering = ['-id']
        verbose_name = "Критерий"
        verbose_name_plural = "Критерии"

    def __str__(self):
        if self.number is None or self.number == "":
            return self.name
        return  f'{self.number}. {self.name}'


# Signal to calculate points in Report and Section when a Section is modified
@receiver(m2m_changed, sender=Section.fields.through)
def update_section_points(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        # Recalculate points for the Section instance
        section_points = instance.fields.aggregate(Sum('points'))['points__sum'] or 0
        Section.objects.filter(pk=instance.pk).update(points=section_points)
        
        # Update the points of the related Report
        report = instance.report
        report_points = report.sections.aggregate(Sum('points'))['points__sum'] or 0
        Report.objects.filter(pk=report.pk).update(points=report_points)

        school_reports = SchoolReport.objects.filter(report=instance.report)
        #Delete answers for questions that are not in the section
        questions = Field.objects.filter(sections__in=instance.report.sections.all())
        Answer.objects.filter(s_report__report=instance.report).exclude(question__in=questions).delete()
        #Add answers for questions that are in the section but not in the school report
        for question in questions:
            if not Answer.objects.filter(s_report__in=school_reports, question=question).exists():
                for school_report in school_reports:
                    Answer.objects.create(s_report=school_report, question=question)
        #Recalculate points for school reports
        for school_report in school_reports:
            try:
                points_sum = round(Answer.objects.filter(s_report=school_report).aggregate(Sum('points'))['points__sum'], 1)
            except:
                points_sum = 0
            if points_sum < school_report.report.yellow_zone_min:
                report_zone = 'R'
            elif points_sum >= school_report.report.green_zone_min:
                report_zone = 'G'
            else:
                report_zone = 'Y'
            school_report.points = points_sum
            school_report.zone = report_zone
            school_report.save()


class Field(models.Model):
    number = models.CharField('Номер показатель', null=False, blank=False, max_length=500)
    name = models.CharField("Название показателя", max_length=750, null=False, blank=False)
    points = models.DecimalField(
        "Макс. баллов", max_digits=5,
        decimal_places=1, null=False, blank=False, default=0
    )
    ANSWER_TYPES = [
        ('BL', "Бинарный выбор (Да/Нет)"),
        ('LST', "Выбор из списка"),
        ('NMBR', "Числовое значение"),
        ('PRC', "Процент"),
    ]
    answer_type = models.CharField(
        "Тип ответа", choices=ANSWER_TYPES, max_length=5, blank=False, null=False
    )
    bool_points = models.DecimalField(
        "Баллы (если бинарный выбор)",
        max_digits=5,
        decimal_places=1,
        default=0,
    )

    attachment_name = models.CharField("Название вложения", max_length=750, default="", null=True, blank=True)
    ATTACHMENT_TYPES = [
        ('DC', "Документ (прикреплённый файл)"),
        ('LNK', 'Ссылка'),
        ('LDC', "Документ или ссылка"),
        ('OTH', 'Иной источник (без ссылки/файла)'),
    ]
    attachment_type = models.CharField(
        "Тип вложения", max_length=3, 
        choices=ATTACHMENT_TYPES,
        default='OTH',
        blank=True, null=True
    )

    note = tinymce_models.HTMLField(
        "Примечание", null=True, blank=True, default=None
    )

    class Meta:
        ordering = ['number']
        verbose_name = "Показатель"
        verbose_name_plural = "Показатели"

    def __str__(self):
        return  f'(id: {self.id}) {self.number}. {self.name}'


@receiver(post_save, sender=Field, dispatch_uid='option_save_signal')
def count_points(sender, instance, using, **kwargs):
    field = instance
    match instance.answer_type:
        case 'BL':
            try: field.points = instance.bool_points
            except: pass
        case 'LST':
            try: field.points = Option.objects.filter(question=instance).aggregate(Max('points'))['points__max']
            except: pass
        case 'NMBR':
            try: field.points = RangeOption.objects.filter(question=instance).aggregate(Max('points'))['points__max']
            except: pass
        case 'PRC':
            try: field.points = RangeOption.objects.filter(question=instance).aggregate(Max('points'))['points__max']
            except: pass
    if field.points == None:
        field.points = 0
    Field.objects.filter(pk=field.pk).update(points=field.points)

    # Update the points of the related Sections
    sections = field.sections.all()
    for section in sections:
        section_points = section.fields.aggregate(Sum('points'))['points__sum'] or 0
        Section.objects.filter(pk=section.pk).update(points=section_points)
        
        # Update the points of the related Report
        report = section.report
        report_points = report.sections.aggregate(Sum('points'))['points__sum'] or 0
        Report.objects.filter(pk=report.pk).update(points=report_points)
    


class Option(models.Model):
    name = models.CharField("Название", max_length=500, blank=False, null=False)
    question = models.ForeignKey(
        Field,
        verbose_name='критерий',
        related_name='options',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    yellow_zone_min = models.DecimalField(
        "Жёлтая зона (минимум)", max_digits=5,
        decimal_places=1, null=True, blank=True, default=None

    )
    green_zone_min = models.DecimalField(
        "Зеленая зона (минимум)", max_digits=5, decimal_places=1,
        null=True, blank=True, default=None
    )
    points = models.DecimalField(
        "Колво баллов",
        max_digits=5,
        decimal_places=1,
        default=0
    )
    ZONE_TYPES = [
        ('R', "Красная"),
        ('Y', "Желтая"),
        ('G', "Зеленая"),
    ]
    zone = models.CharField(
        "Зона", choices=ZONE_TYPES, max_length=5, blank=False, null=False
    )

    class Meta:
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответа"

    def __str__(self):
        return self.name

@receiver(post_save, sender=Option, dispatch_uid='option_save_signal')
def count_points(sender, instance, using, **kwargs):
    instance = instance.question
    match instance.answer_type:
        case 'BL':
            try: field_points = instance.bool_points
            except: pass
        case 'LST':
            try: field_points = Option.objects.filter(question=instance).aggregate(Max('points'))['points__max']
            except: pass
        case 'NMBR':
            try: field_points = RangeOption.objects.filter(question=instance).aggregate(Max('points'))['points__max']
            except: pass
        case 'PRC':
            try: field_points = RangeOption.objects.filter(question=instance).aggregate(Max('points'))['points__max']
            except: pass
    if field_points == None:
        field_points = 0
    if instance.points != field_points and field_points is not None:
        instance.points = field_points
        instance.save()
    sections = instance.sections.all()
    for section in sections:
        report = section.report
        report.points = count_report_points(report)
        report.save()
    utils.count_answers_points(instance.answers.all())
    school_reports = SchoolReport.objects.filter(report__sections__in=instance.sections.all())
    for school_report in school_reports:
        try:
            points_sum = round(Answer.objects.filter(s_report=school_report).aggregate(Sum('points'))['points__sum'], 1)
        except:
            points_sum = 0
        if points_sum < school_report.report.yellow_zone_min:
            report_zone = 'R'
        elif points_sum >= school_report.report.green_zone_min:
            report_zone = 'G'
        else:
            report_zone = 'Y'
        school_report.points = points_sum
        school_report.zone = report_zone
        school_report.save()


class RangeOption(models.Model):
    question = models.ForeignKey(
        Field,
        verbose_name='критерий',
        related_name='range_options',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    RANGE_TYPES = [
        ('L', "Меньше или равно"),
        ('G', "Больше или равно"),
        ('D', "Диапазон"),
        ('E', "Равно"),
    ]
    range_type = models.CharField(
        "Тип условия", choices=RANGE_TYPES, max_length=1, blank=False, null=False, default='D'
    )
    ZONE_TYPES = [
        ('R', "Красная"),
        ('Y', "Желтая"),
        ('G', "Зеленая"),
    ]
    zone = models.CharField(
        "Зона", choices=ZONE_TYPES, max_length=5, blank=False, null=False
    )
    less_or_equal = models.DecimalField(
        "Меньше или равно",
        max_digits=5,
        decimal_places=1,
        null=True, blank=True,
        default=None

    )
    greater_or_equal = models.DecimalField(
        "Больше или равно",
        max_digits=5,
        decimal_places=1,
        null=True, blank=True,
        default=None
    )
    equal = models.DecimalField(
        "Равно",
        max_digits=5,
        decimal_places=1,
        null=True, blank=True,
        default=None
    )
    points = models.DecimalField(
        "Колво баллов",
        max_digits=5,
        decimal_places=1,
        default=0
    )
    yellow_zone_min = models.DecimalField(
        "Жёлтая зона (минимум)", max_digits=5,
        decimal_places=1, null=True, blank=True, default=None

    )
    green_zone_min = models.DecimalField(
        "Зеленая зона (минимум)", max_digits=5, decimal_places=1,
        null=True, blank=True, default=None
    )

    class Meta:
        verbose_name = "Диапозон"
        verbose_name_plural = "Диапазоны"

    def __str__(self):
        return f"{self.question} ({self.range_type})"


@receiver(post_save, sender=RangeOption, dispatch_uid='option_save_signal')
def count_points(sender, instance, using, **kwargs):
    instance = instance.question
    match instance.answer_type:
        case 'BL':
            try: field_points = instance.bool_points
            except: pass
        case 'LST':
            try: field_points = Option.objects.filter(question=instance).aggregate(Max('points'))['points__max']
            except: pass
        case 'NMBR':
            try: field_points = RangeOption.objects.filter(question=instance).aggregate(Max('points'))['points__max']
            except: pass
        case 'PRC':
            try: field_points = RangeOption.objects.filter(question=instance).aggregate(Max('points'))['points__max']
            except: pass
    if field_points == None:
        field_points = 0
    if instance.points != field_points and field_points is not None:
        instance.points = field_points
        instance.save()
    sections = instance.sections.all()
    for section in sections:
        report = section.report
        report.points = count_report_points(report)
        report.save()



class SchoolReport(models.Model):
    report = models.ForeignKey(
        Report,
        verbose_name='Отчёт',
        related_name='schools',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    school = models.ForeignKey(
        School,
        verbose_name='Школа',
        related_name='reports',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    STATUSES = [
        ('C', "Заполнение"),
        ('A', "На согласовании в ТУ/ДО"),
        ('B', "Отправлено в МинОбр"),
        ('D', "Принят")
    ]
    status = models.CharField(
        "Статус", choices=STATUSES, max_length=1, blank=False, null=False, default='C'
    )
    is_ready = models.BooleanField(
        "Готов к отправке?", default=False
    )
    points = models.DecimalField(
        "Колво баллов",
        max_digits=5,
        decimal_places=1,
        default=0
    )
    ZONE_TYPES = [
        ('R', "Красная"),
        ('Y', "Желтая"),
        ('G', "Зеленая"),
    ]
    zone = models.CharField(
        "Зона", choices=ZONE_TYPES, max_length=5, blank=False, null=False, default='R'
    )

    class Meta:
        verbose_name = "Отчёт"
        verbose_name_plural = "Отчёты"

    def __str__(self):
        return  f'{self.school} ({self.report})'

@receiver(pre_save, sender=SchoolReport)
def accept(sender, instance, **kwargs):
    pass
    #instance.status = 'D'


class SectionSreport(models.Model):
    s_report = models.ForeignKey(
        SchoolReport,
        verbose_name='отчёт',
        related_name='sections',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    section = models.ForeignKey(
        Section,
        verbose_name='раздел',
        related_name='s_reports',
        on_delete=CASCADE,
        null=True, blank=True 
    )
    points = models.DecimalField(
        "Колво баллов",
        max_digits=5,
        decimal_places=1,
        default=0
    )
    ZONE_TYPES = [
        ('R', "Красная"),
        ('Y', "Желтая"),
        ('G', "Зеленая"),
    ]
    zone = models.CharField(
        "Зона", choices=ZONE_TYPES, max_length=5, blank=False, null=False, default='R'
    )

    class Meta:
        verbose_name = "Раздел отчёта школы"
        verbose_name_plural = "Разделы отчётов школ"

    def __str__(self):
        return f'{self.section} ({self.points})'
    

class Answer(models.Model):
    s_report = models.ForeignKey(
        SchoolReport,
        verbose_name='отчёт',
        related_name='answers',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    question = models.ForeignKey(
        Field,
        verbose_name='критерий',
        related_name='answers',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    option = models.ForeignKey(
        Option,
        verbose_name='опция',
        related_name='answers',
        on_delete=CASCADE,
        null=True, blank=False 
    )
    points = models.DecimalField(
        "Колво баллов",
        max_digits=5,
        decimal_places=1,
        default=0
    )
    number_value = models.DecimalField(
        "Числовое значение",
        max_digits=5,
        decimal_places=1,
        default=0
    )
    bool_value = models.BooleanField(
        "Бинарный выбор", default=False, null=True
    )
    ZONE_TYPES = [
        ('R', "Красная"),
        ('Y', "Желтая"),
        ('G', "Зеленая"),
    ]
    zone = models.CharField(
        "Зона", choices=ZONE_TYPES, max_length=5, blank=False, null=False, default='R'
    )

    is_mod_by_ter = models.BooleanField(
        "Изменён ТУ/ДО?", default=False
    )
    is_mod_by_mo = models.BooleanField(
        "Изменён МинОбром?", default=False
    )

    def file_path(instance, filename):
        return 'media/reports/{0}'.format(filename)
    file = models.FileField("Файл", upload_to=file_path, max_length=200, null=True, blank=True)
    link = models.CharField("Ссылка", max_length=1500, blank=True, null=True)
    
    
    class Meta:
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"

    def __str__(self):
        return  f'{self.question}'


class ReportLink(models.Model):
    s_report = models.ForeignKey(
        SchoolReport,
        verbose_name='отчёт',
        related_name='links',
        on_delete=CASCADE,
        blank=False 
    )
    answer = models.ForeignKey(
        Answer,
        verbose_name='ответ',
        related_name='links',
        on_delete=CASCADE,
        blank=False 
    )
    link = models.CharField("Ссылка", max_length=1500, blank=True, null=True)

    class Meta:
        verbose_name = "Ссылка"
        verbose_name_plural = "Ссылки"

    def __str__(self):
        return  f'{self.link}'

class ReportFile(models.Model):
    s_report = models.ForeignKey(
        SchoolReport,
        verbose_name='отчёт',
        related_name='files',
        on_delete=CASCADE,
        blank=False 
    )
    answer = models.ForeignKey(
        Answer,
        verbose_name='условие',
        related_name='files',
        on_delete=CASCADE,
        blank=False 
    )

    def file_path(instance, filename):
        return 'media/reports/{0}'.format(filename)
    file = models.FileField("Файл", upload_to=file_path, max_length=200, null=True, blank=True)

    class Meta:
        verbose_name = "Файл"
        verbose_name_plural = "Файлы"

    def __str__(self):
        return  f'{self.file.name} (файл)'
    

@receiver(models.signals.post_delete, sender=ReportFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)


@receiver(models.signals.pre_save, sender=ReportFile)
def auto_delete_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return False

    try:
        old_file = ReportFile.objects.get(pk=instance.pk).file
    except ReportFile.DoesNotExist:
        return False

    new_file = instance.file
    if not old_file == new_file and old_file.name is not None and old_file.name != "":
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)