from django.db import models, transaction
from django.db.models.deletion import CASCADE, SET_NULL
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging

from users.models import User

from tinymce import models as tinymce_models

# Настройка логирования
logger = logging.getLogger(__name__)


# Create your models here.
class TerAdmin(models.Model):
    name = models.CharField("Название", max_length=250)
    
    representatives = models.ManyToManyField(
        User, 
        verbose_name="Представитель ТУ/ДО", 
        related_name="ter_admin", 
        blank=True,
    )

    class Meta:
        verbose_name = "ТУ/ДО"
        verbose_name_plural = "ТУ/ДО"

    def __str__(self):
        return  f"{self.name}"


class SchoolCloster(models.Model):
    name = models.CharField("Название", max_length=250) 

    class Meta:
        verbose_name = "Кластер"
        verbose_name_plural = "Кластеры"

    def __str__(self):
        return  self.name


class SchoolType(models.Model):
    name = models.CharField("Полное наименование", max_length=250)
    short_name = models.CharField("Сокращенное наименование", max_length=125)

    class Meta:
        verbose_name = "Тип учебного учреждения"
        verbose_name_plural = "Типы учебных учреждений"

    def __str__(self):
        return  self.short_name


class School(models.Model):
    ais_id = models.IntegerField(
        "ID в АИС \"Кадры в образовании\"", blank=False, null=True, unique=True
    )
    name = models.CharField("Полное наименование", max_length=1000, blank=False, null=True)
    short_name = models.CharField("Сокращенное наименование", max_length=500, blank=False, null=True)
    email = models.EmailField("Официальный email",  blank=False, null=True)
    city = models.CharField("Населённый пункт", max_length=250, blank=False, null=True)
    number = models.CharField("Номер/название школы", max_length=50, blank=True, null=True)
    is_archived = models.BooleanField("Архивная школа", default=False, help_text="При активации этого статуса школа и её отчеты скрываются из пользовательского интерфейса, а аккаунт школы деактивируется.")
    
    school_type = models.ForeignKey(
        SchoolType, 
        verbose_name="Тип школы",
        related_name="schools",
        blank=True,
        null=True,
        on_delete=CASCADE
    )
    closter = models.ForeignKey(
        SchoolCloster, 
        verbose_name="Кластер",
        related_name="schools",
        blank=True,
        null=True,
        on_delete=CASCADE
    )
    ter_admin = models.ForeignKey(
        TerAdmin, 
        verbose_name="ТУ/ДО",
        related_name="schools",
        blank=False,
        null=False,
        on_delete=CASCADE
    )
    principal = models.OneToOneField(
        User, 
        verbose_name="Директор", 
        related_name="school", 
        blank=True,
        null=True,
        on_delete=SET_NULL
    )

    SCHOOL_LEVELS = [
        ('A', "1 — 11 классы"),
        ('M', "1 — 9 классы"),
        ('S', "1 — 4 классы"),
        ('G', "10 — 11 классы"),
        ('MG', "5 — 11 классы"),
    ]
    ed_level = models.CharField(
        "Уровень образования", choices=SCHOOL_LEVELS, max_length=4, blank=True, null=True
    )

    class Meta:
        verbose_name = "Школа"
        verbose_name_plural = "Школы"

    def __str__(self):
        if self.school_type is None:
            return self.short_name
        elif self.number is None:
            return f"{self.school_type} ({self.city})"
        elif any(char.isdigit() for char in str(self.number)):
            return f"{self.school_type} №{self.number} ({self.city})"
        else:
            return f"{self.school_type} {self.number} ({self.city})"
    


class QuestionCategory(models.Model):
    name = models.CharField("Название", max_length=250)
    description = models.TextField("Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Категория вопроса"
        verbose_name_plural = "Категории вопросов"

    def __str__(self):
        return self.name
    

class Question(models.Model):
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)
    short_question = models.CharField("Вопрос", max_length=250, blank=False, null=False)
    question = tinymce_models.HTMLField("Пояснение", null=True, blank=True)
    
    category = models.ForeignKey(
        QuestionCategory, 
        verbose_name="Категория",
        related_name="questions",
        blank=False,
        null=False,
        on_delete=CASCADE
    )
    user = models.ForeignKey(
        User, 
        verbose_name="Пользователь",
        related_name="questions",
        blank=True,
        null=True,
        on_delete=CASCADE
    )

    answer = tinymce_models.HTMLField(
        "Ответ", null=True, blank=True, default=None
    )
    is_resolved = models.BooleanField("Решено", default=False)
    answer_at = models.DateTimeField("Дата ответа", blank=True, null=True)
    is_visible = models.BooleanField("Отображать на сайте", default=False)

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"

    def __str__(self):
        return self.short_question

# Ведение лога изменений статуса архивации
@receiver(pre_save, sender=School)
def log_archive_status_changes(sender, instance, **kwargs):
    """Логирует изменения статуса архивации школы"""
    if instance.pk:  # Если это существующая школа (не новая)
        try:
            # Получаем текущее состояние школы из базы данных
            old_instance = School.objects.get(pk=instance.pk)
            
            # Если статус архивации изменился
            if old_instance.is_archived != instance.is_archived:
                action = "архивирована" if instance.is_archived else "разархивирована"
                logger.info(f"Школа {instance.name} (ID: {instance.pk}) {action}")
        except School.DoesNotExist:
            pass  # Школа новая, ничего не делаем

# Обработчик изменения статуса архивации школы
@receiver(post_save, sender=School)
def handle_school_archive_status(sender, instance, **kwargs):
    # Если школа архивирована и у неё есть директор
    if instance.is_archived and instance.principal:
        # Деактивируем аккаунт директора
        if instance.principal.is_active:
            logger.info(f"Деактивация аккаунта директора школы {instance.name} (ID: {instance.id}) в связи с архивацией")
            instance.principal.is_active = False
            instance.principal.save()
    # Если школа разархивирована и у неё есть директор
    elif not instance.is_archived and instance.principal:
        # Активируем аккаунт директора, если он был деактивирован
        if not instance.principal.is_active:
            logger.info(f"Активация аккаунта директора школы {instance.name} (ID: {instance.id}) в связи с разархивацией")
            instance.principal.is_active = True
            instance.principal.save()

# Обработчик изменения данных школы для проверки актуальности отчетов
@receiver(post_save, sender=School)
def check_school_reports_relevance(sender, instance, **kwargs):
    """
    Проверяет актуальность всех отчетов школы при изменении ее данных.
    Если кластер или уровень образования школы изменились, отмечает отчеты как устаревшие.
    """
    if instance.pk:  # Если это существующая школа (не новая)
        try:
            # Импортируем модели здесь, чтобы избежать циклических импортов
            from reports.models import SchoolReport
            
            # Получаем все отчеты школы со статусом "Принят"
            school_reports = SchoolReport.objects.filter(school=instance, status='D')
            
            if school_reports.exists():
                logger.info(f"Проверка актуальности отчетов школы {instance.name} (ID: {instance.id})")
                
                # Проверяем каждый отчет на актуальность
                for report in school_reports:
                    report.check_relevance()
                
        except Exception as e:
            logger.error(f"Ошибка при проверке отчетов школы {instance.name} (ID: {instance.id}): {str(e)}")
