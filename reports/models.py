import os
from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL
from django.db.models.signals import pre_save
from django.dispatch import receiver

from tinymce import models as tinymce_models

from reports.utils import create_report_notifications
from users.models import Notification, User
from schools.models import School, SchoolCloster


class Report(models.Model):
    year = models.IntegerField('Год', null=False, blank=False)
    name = models.CharField("Название отчёта", max_length=750)
    is_published = models.BooleanField(
        "Опубликовать?", default=False
    )

    class Meta:
        verbose_name = "Отчёт (шаблон)"
        verbose_name_plural = "Отчёты (шаблон)"

    def __str__(self):
        return  f'{self.name} ({self.year})'


@receiver(pre_save, sender=Report, dispatch_uid='report_save_signal')
def create_notification(sender, instance, using, **kwargs):
    if instance.is_published:
        if instance.id is None:
                create_report_notifications(instance)
        elif Report.objects.get(id=instance.id).is_published == False:
            create_report_notifications(instance)



class ReportZone(models.Model):
    report = models.ForeignKey(
        Report,
        verbose_name='отчёт',
        related_name='zones',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    closter = models.ForeignKey(
        SchoolCloster,
        verbose_name='Кластер',
        related_name='zones',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    ZONE_TYPES = [
        ('R', "Красная"),
        ('Y', "Желтая"),
        ('G', "Зеленая"),
    ]
    zone = models.CharField(
        "Зона", choices=ZONE_TYPES, max_length=5, blank=False, null=False
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
    RANGE_TYPES = [
        ('L', "Меньше или равно"),
        ('G', "Больше или равно"),
        ('D', "Диапазон"),
    ]
    range_type = models.CharField(
        "Тип условия", choices=RANGE_TYPES, max_length=1, blank=False, null=False
    )
    less_or_equal = models.DecimalField(
        "Меьньше или равно", max_digits=5,
        decimal_places=1, null=True, blank=True, default=None

    )
    greater_or_equal = models.DecimalField(
        "Больше или равно", max_digits=5, decimal_places=1,
        null=True, blank=True, default=None
    )

    class Meta:
        verbose_name = "Зона"
        verbose_name_plural = "Зоны"

    def __str__(self):
        return  f'{self.report}, {self.get_ed_level_display()} ({self.zone})'


class Attachment(models.Model):
    name = models.CharField("Название вложения", max_length=750)
    report = models.ForeignKey(
        Report,
        verbose_name='отчёт',
        related_name='attachments',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    ATTACHMENT_TYPES = [
        ('DC', "Документ (прикреплённый файл)"),
        ('LNK', 'Ссылка'),
    ]
    attachment_type = models.CharField(
        "Цель обучения", max_length=3, 
        choices=ATTACHMENT_TYPES, 
        blank=True, null=True
    )

    class Meta:
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения"

    def __str__(self):
        return f'{self.name} ({self.get_attachment_type_display()})'


class Section(models.Model):
    number = models.CharField('Номер раздела', null=True, blank=True, max_length=500)
    name = models.CharField("Название раздела", max_length=500)
    report = models.ForeignKey(
        Report,
        verbose_name='отчёт',
        related_name='sections',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    note = tinymce_models.HTMLField(
        "Примечание", null=True, blank=True, default=None
    )

    class Meta:
        verbose_name = "Раздел отчёта"
        verbose_name_plural = "Разделы отчётов"

    def __str__(self):
        if self.number is None or self.number == "":
            return self.name
        return  f'{self.number}. {self.name}'


class Field(models.Model):
    number = models.CharField('Номер поля', null=False, blank=False, max_length=500)
    name = models.CharField("Название раздела", max_length=750, null=False, blank=False)
    section = models.ForeignKey(
        Section,
        verbose_name='раздел',
        related_name='fields',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    note = tinymce_models.HTMLField(
        "Примечание", null=True, blank=True, default=None
    )

    class Meta:
        verbose_name = "Показатель"
        verbose_name_plural = "Показатели"

    def __str__(self):
        return  f'{self.section.number}.{self.number}. {self.name}'



class Question(models.Model):
    name = models.CharField("Название критерия", max_length=750, null=True, blank=True)
    field = models.ForeignKey(
        Field,
        verbose_name='показатель',
        related_name='questions',
        on_delete=CASCADE,
        null=False, blank=False 
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
    note = tinymce_models.HTMLField(
        "Примечание", null=True, blank=True, default=None
    )

    class Meta:
        verbose_name = "Критерий"
        verbose_name_plural = "Критерии"

    def __str__(self):
        return  f'{self.name} ({self.get_answer_type_display()})' 


class Option(models.Model):
    name = models.CharField("Название", max_length=250, blank=False, null=False)
    question = models.ForeignKey(
        Question,
        verbose_name='критерий',
        related_name='options',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    points = models.DecimalField(
        "Колво баллов",
        max_digits=5,
        decimal_places=1,
        default=0
    )

    class Meta:
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответа"

    def __str__(self):
        return self.name


class RangeOption(models.Model):
    question = models.ForeignKey(
        Question,
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
        "Тип условия", choices=RANGE_TYPES, max_length=1, blank=False, null=False
    )
    less_or_equal = models.DecimalField(
        "Меьньше или равно",
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

    class Meta:
        verbose_name = "Диапозон"
        verbose_name_plural = "Диапазоны"

    def __str__(self):
        return f"{self.question} ({self.range_type})"
    

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
        ('B', "На согласовании в МинОбр"),
        ('D', "Принят")
    ]
    status = models.CharField(
        "Статус", choices=STATUSES, max_length=1, blank=False, null=False, default='C'
    )
    is_ready = models.BooleanField(
        "Готов к отправке?", default=False
    )

    class Meta:
        verbose_name = "Отчёт"
        verbose_name_plural = "Отчёты"

    def __str__(self):
        return  f'{self.school} ({self.report})'
    


class Answer(models.Model):
    s_report = models.ForeignKey(
        SchoolReport,
        verbose_name='отчёт',
        related_name='answers',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    question = models.ForeignKey(
        Question,
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
    is_mod_by_ter = models.BooleanField(
        "Изменён ТУ/ДО?", default=False
    )
    
    class Meta:
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"

    def __str__(self):
        return  f'{self.question}'


class ReportFile(models.Model):
    s_report = models.ForeignKey(
        SchoolReport,
        verbose_name='отчёт',
        related_name='files',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    attachment = models.ForeignKey(
        Attachment,
        verbose_name='вложение (отчёт)',
        related_name='files',
        on_delete=CASCADE,
        null=False, blank=False 
    )
    def file_path(instance, filename):
        return 'media/reports/{0}'.format(filename)
    file = models.FileField("Файл", upload_to=file_path, max_length=200, null=True, blank=True)

    class Meta:
        verbose_name = "Файл"
        verbose_name_plural = "Файлы"

    def __str__(self):
        return  f'{self.attachment.name} (файл)'
    

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