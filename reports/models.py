import os
from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL
from django.db.models.signals import pre_save, post_save, m2m_changed
from django.dispatch import receiver
from django.db.models import Sum, Max
from django.urls import reverse
import logging
from datetime import datetime, timedelta
from django.utils import timezone

from tinymce import models as tinymce_models

from users.models import Notification, User
from schools.models import School, SchoolCloster
# Import utils separately to avoid circular imports
from reports import utils

logger = logging.getLogger(__name__)

from reports import utils
from reports.utils import count_report_points, create_report_notifications
from reports.utils import count_points as reports_count_points
from reports.utils import select_range_option

from django.core.cache import cache
from common.utils import get_cache_key


class Year(models.Model):
    """
    Модель для управления годами отчетности
    """
    YEAR_STATUS_CHOICES = [
        ('forming', 'Формирование отчётов'),
        ('updating', 'Обновление школ ТУ/ДО'),
        ('filling', 'Заполнение и проверка отчётов'),
        ('completed', 'Завершено'),
    ]
    
    year = models.IntegerField("Год", unique=True)
    status = models.CharField(
        "Статус", 
        max_length=20, 
        choices=YEAR_STATUS_CHOICES, 
        default='forming',
        help_text="""
        'Формирование отчётов' - отчёты этого года школ не формируются;
        'Обновление школ ТУ/ДО' - даёт возможность редактировать школы пользователям с ролью «ТУ/ДО»;
        'Заполнение и проверка отчётов' - активная фаза работы с отчетами;
        'Завершено' - закрыт доступ к редактированию шаблонов и отчётов школ этого года
        """
    )
    is_current = models.BooleanField(
        "Текущий год?", 
        default=False,
        help_text="Отметьте, если это текущий рабочий год"
    )
    
    class Meta:
        verbose_name = "Год"
        verbose_name_plural = "Годы"
        ordering = ['-year']
    
    def __str__(self):
        return f"{self.year}"
    
    def save(self, *args, **kwargs):
        """
        Переопределение метода save для обеспечения того, чтобы только один год был текущим
        """
        if self.is_current:
            # Если этот год установлен как текущий, отменить текущий статус всех других годов
            Year.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        
        super().save(*args, **kwargs)


class Report(models.Model):
    year = models.ForeignKey(
        Year,
        verbose_name='Год',
        related_name='reports',
        on_delete=models.CASCADE,
        null=False, blank=False
    )
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
    years = models.ManyToManyField(
        Year,
        verbose_name='Годы',
        related_name='fields',
        blank=True
    )
    points = models.DecimalField(
        "Макс. баллов", max_digits=5,
        decimal_places=1, null=False, blank=False, default=0
    )
    ANSWER_TYPES = [
        ('BL', "Бинарный выбор (Да/Нет)"),
        ('LST', "Выбор из списка"),
        ('NMBR', "Числовое значение"),
        ('PRC', "Процент"),
        ('MULT', "Множественный выбор"),
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
    max_points = models.DecimalField(
        "Макс. баллов (для множественного выбора)",
        max_digits=5,
        decimal_places=1,
        null=True, blank=True,
        default=None
    )
    yellow_zone_min = models.DecimalField(
        "Жёлтая зона (минимум)", max_digits=5,
        decimal_places=1, null=True, blank=True, default=None
    )
    green_zone_min = models.DecimalField(
        "Зеленая зона (минимум)", max_digits=5,
        decimal_places=1, null=True, blank=True, default=None
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
        case 'MULT':
            if instance.max_points:
                try: field.points = instance.max_points
                except: pass
            else:
                # Если максимальные баллы не указаны, используем сумму баллов всех опций
                try: field.points = Option.objects.filter(question=instance).aggregate(Sum('points'))['points__sum']
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
    number = models.IntegerField("Номер", default=0)
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
        ordering = ['number']

    def __str__(self):
        return self.name

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


# Кастомный менеджер для SchoolReport, который исключает отчеты, помеченные на удаление
class ActiveSchoolReportManager(models.Manager):
    """Менеджер, который исключает отчеты, помеченные на удаление"""
    
    def get_queryset(self):
        # Возвращает только активные отчеты (не помеченные на удаление)
        return super().get_queryset().filter(is_marked_for_deletion=False)

# Кастомный менеджер для SchoolReport, который возвращает все отчеты, включая помеченные на удаление
class AllSchoolReportManager(models.Manager):
    """Менеджер, который возвращает все отчеты, включая помеченные на удаление"""
    
    def get_queryset(self):
        return super().get_queryset()

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
    
    # Поля для отложенного удаления
    is_marked_for_deletion = models.BooleanField(
        "Отмечен на удаление", default=False,
        help_text="Если отмечено, отчёт будет удален после истечения срока"
    )
    deletion_date = models.DateTimeField(
        "Дата удаления", blank=True, null=True,
        help_text="Дата, когда отчёт будет фактически удален"
    )

    # Поле для отметки устаревших отчетов
    is_outdated = models.BooleanField(
        "Устаревший отчет", default=False,
        help_text="Отмечается, если кластер или уровень образования школы изменились после создания отчета"
    )

    # Менеджеры модели
    # objects будет возвращать только активные отчеты - это менеджер по умолчанию
    objects = ActiveSchoolReportManager()
    # admin_objects будет возвращать все отчеты, включая помеченные на удаление
    admin_objects = AllSchoolReportManager()

    class Meta:
        verbose_name = "Отчёт школы"
        verbose_name_plural = "Отчёты школ"

    def __str__(self):
        return f"{self.school} ({self.report})"
        
    def check_relevance(self):
        """
        Проверяет актуальность отчета на основе текущих данных школы.
        Отчет считается устаревшим, если его кластер или уровень образования не соответствуют текущим данным школы.
        """
        report_is_relevant = True
        
        # Проверяем соответствие кластера
        if self.school.closter != self.report.closter:
            report_is_relevant = False
            
        # Проверяем соответствие уровня образования
        if self.school.ed_level != self.report.ed_level:
            report_is_relevant = False
            
        # Обновляем статус актуальности отчета, если он изменился
        if self.is_outdated != (not report_is_relevant):
            self.is_outdated = not report_is_relevant
            self.save(update_fields=['is_outdated'])
            
        return report_is_relevant

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
        null=True, blank=True
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
    selected_options = models.ManyToManyField(
        Option,
        verbose_name='выбранные опции',
        related_name='multiple_answers',
        blank=True
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
    
    is_checked = models.BooleanField(
        "Проверено", default=False
    )
    checked_by = models.ForeignKey(
        'users.User',
        verbose_name='Проверил',
        related_name='checked_answers',
        on_delete=SET_NULL,
        null=True,
        blank=True
    )
    checked_at = models.DateTimeField(
        "Дата проверки",
        auto_now_add=True,
        null=True,
        blank=True
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

@receiver(post_save, sender='reports.Answer')
def update_sections_on_answer_save(sender, instance, created, **kwargs):
    """
    Signal receiver to update SectionSreport when an Answer is saved
    """
    if instance.s_report_id:
        utils.update_section_sreports(instance.s_report)

@receiver(post_save, sender=SchoolReport)
def invalidate_dashboard_cache(sender, instance, **kwargs):
    """Invalidate all dashboard caches for this report"""
    # Create a key that includes the report id
    cache_key = get_cache_key('ter_admins_dash', 
        year=instance.report.year,
        report=str(instance.report_id)
    )
    cache.delete(cache_key)

@receiver(post_save, sender=Answer)
def invalidate_dashboard_caches(sender, instance, **kwargs):
    """
    Signal receiver to invalidate dashboard caches when an Answer is saved
    """
    try:
        s_report = instance.s_report
        school = s_report.school
        year = s_report.report.year
        
        # Clear all ter_admins_dash caches for this ter_admin and year
        schools = School.objects.filter(ter_admin=school.ter_admin, is_archived=False)
        reports = Report.objects.filter(year=year)
        
        # Generate all possible cache key combinations
        for s in schools:
            for r in reports:
                cache_key = get_cache_key('ter_admins_dash',
                    year=year,
                    schools=str(s.id),
                    reports=str(r.id)
                )
                cache.delete(cache_key)
                
                # Also try the combined format
                cache_key = get_cache_key('ter_admins_dash',
                    year=year,
                    schools=','.join(sorted(str(school.id) for school in schools)),
                    reports=','.join(sorted(str(report.id) for report in reports))
                )
                cache.delete(cache_key)
        
        # Clear closters_report cache
        cache_key = get_cache_key('closters_report_data',
            year=year,
            ter_admin=str(school.ter_admin.id),
            closters=str(school.closter.id) if school.closter else '',
            ed_levels=school.ed_level
        )
        cache.delete(cache_key)
        
        # Clear any other potential cache keys
        cache.delete(f'ter_admins_dash_{year}')
        cache.delete(f'closters_report_{year}')
        
    except Exception as e:
        logger.error(f"Error invalidating cache for Answer {instance.id}: {str(e)}")

def calculate_field_points(field):
    """Calculate maximum points for a field based on its answer type"""
    match field.answer_type:
        case 'BL':
            return field.bool_points
        case 'LST':
            return Option.objects.filter(question=field).aggregate(Max('points'))['points__max'] or 0
        case 'NMBR' | 'PRC':
            return RangeOption.objects.filter(question=field).aggregate(Max('points'))['points__max'] or 0
        case 'MULT':
            if field.max_points is not None:
                return field.max_points
            else:
                return Option.objects.filter(question=field).aggregate(Sum('points'))['points__sum'] or 0
    return 0

def update_school_report_points(school_report):
    """Update points and zone for a school report"""
    try:
        points_sum = round(Answer.objects.filter(
            s_report=school_report
        ).aggregate(Sum('points'))['points__sum'] or 0, 1)
    except:
        points_sum = 0
        
    # Determine zone based on points
    if points_sum < school_report.report.yellow_zone_min:
        report_zone = 'R'
    elif points_sum >= school_report.report.green_zone_min:
        report_zone = 'G'
    else:
        report_zone = 'Y'
        
    SchoolReport.objects.filter(pk=school_report.pk).update(
        points=points_sum,
        zone=report_zone
    )

def invalidate_caches_for_report(year, school):
    """Centralized cache invalidation for reports"""
    # Clear main dashboard caches
    cache_keys = [
        f'ter_admins_dash_{year}',
        f'closters_report_{year}'
    ]
    
    # Get the first report for this school and year
    first_report = school.reports.filter(report__year=year).first()
    
    # Add additional cache keys only if a report exists
    if first_report:
        cache_keys.extend([
            get_cache_key('ter_admins_dash',
                year=year,
                schools=str(school.id),
                reports=str(first_report.report_id)
            ),
            get_cache_key('closters_report_data',
                year=year,
                ter_admin=str(school.ter_admin.id),
                closters=str(school.closter.id) if school.closter else '',
                ed_levels=school.ed_level
            )
        ])
    
    cache.delete_many(cache_keys)

def update_field_and_reports(question):
    """Update field points and related reports"""
    # Update field points
    field_points = calculate_field_points(question)
    Field.objects.filter(pk=question.pk).update(points=field_points)
    
    # Get affected reports and schools
    affected_reports = Report.objects.filter(sections__fields=question)
    affected_schools = School.objects.filter(reports__report__in=affected_reports, is_archived=False).distinct()
    
    # Bulk update school reports
    for school in affected_schools:
        school_reports = SchoolReport.objects.filter(
            school=school,
            report__in=affected_reports
        )
        for sr in school_reports:
            update_school_report_points(sr)
        invalidate_caches_for_report(affected_reports.first().year, school)

@receiver(post_save, sender=Option)
def handle_option_save(sender, instance, **kwargs):
    """Handle Option model save"""
    question = instance.question
    
    # Bulk update affected answers
    Answer.objects.filter(
        question=question,
        option=instance
    ).update(points=instance.points, zone=instance.zone)
    
    # Update field and reports
    update_field_and_reports(question)

@receiver(post_save, sender=RangeOption)
def handle_range_option_save(sender, instance, **kwargs):
    """Handle RangeOption model save"""
    question = instance.question
    
    # Update affected numeric answers
    answers = Answer.objects.filter(question=question).select_related('s_report')
    for answer in answers:
        if answer.number_value is not None:
            r_option = select_range_option(question.range_options.all(), answer.number_value)
            if r_option:
                Answer.objects.filter(id=answer.id).update(
                    points=r_option.points,
                    zone=r_option.zone
                )
            else:
                Answer.objects.filter(id=answer.id).update(
                    points=0,
                    zone='R'
                )
    
    # Update field and reports
    update_field_and_reports(question)

@receiver(post_save, sender=Field)
def handle_field_save(sender, instance, **kwargs):
    """Handle Field model save - recalculate points and zones for all reports with this field"""
    logger.info(f"Field {instance.id} saved - recalculating points for affected reports")
    
    # Since we're already in the Field model, we can just use instance directly
    update_field_and_reports(instance)
    
    # For MULT type fields, we need to update zones for all answers based on yellow_zone_min and green_zone_min
    if instance.answer_type == 'MULT':
        answers = Answer.objects.filter(question=instance).select_related('s_report')
        for answer in answers:
            # Skip answers without points (empty selections)
            if answer.points is None or answer.points == 0:
                continue
                
            # Determine zone based on field settings
            old_zone = answer.zone
            if instance.yellow_zone_min is not None and instance.green_zone_min is not None:
                if answer.points < instance.yellow_zone_min:
                    new_zone = 'R'
                elif answer.points >= instance.green_zone_min:
                    new_zone = 'G'
                else:
                    new_zone = 'Y'
            else:
                # If no zone settings in field, try section
                section = instance.sections.first()
                if section and section.yellow_zone_min is not None and section.green_zone_min is not None:
                    if answer.points < section.yellow_zone_min:
                        new_zone = 'R'
                    elif answer.points >= section.green_zone_min:
                        new_zone = 'G'
                    else:
                        new_zone = 'Y'
                else:
                    # Fallback to simple logic
                    new_zone = 'G' if answer.points > 0 else 'R'
            
            # Update zone if changed
            if old_zone != new_zone:
                logger.info(f"Updating zone for answer {answer.id} from {old_zone} to {new_zone}")
                Answer.objects.filter(id=answer.id).update(zone=new_zone)

class OptionCombination(models.Model):
    field = models.ForeignKey(
        Field,
        verbose_name='показатель',
        related_name='combinations',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    option_numbers = models.CharField("Номера полей (через запятую)", max_length=255, blank=False, null=False)
    points = models.DecimalField(
        "Количество баллов",
        max_digits=5,
        decimal_places=1,
        default=0
    )
    
    class Meta:
        verbose_name = "Комбинация вариантов"
        verbose_name_plural = "Комбинации вариантов"
        
    def __str__(self):
        return f"{self.field} - {self.option_numbers} ({self.points})"