from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL
from django.utils.translation import gettext_lazy as _

from users.models import User

from tinymce import models as tinymce_models


# Create your models here.
class TerAdmin(models.Model):
    name = models.CharField("Название", max_length=250)
    
    representative = models.OneToOneField(
        User, 
        verbose_name="Представитель ТУ/ДО", 
        related_name="ter_admin", 
        blank=True,
        null=True,
        on_delete=SET_NULL
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
    number = models.IntegerField("Номер школы", blank=True, null=True)
    
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
        return f"{self.school_type} №{self.number} ({self.city})"
    


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
