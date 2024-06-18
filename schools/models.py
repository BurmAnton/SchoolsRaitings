from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL
from django.utils.translation import gettext_lazy as _

from users.models import User


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
    inn = models.CharField(
        "ИНН", max_length=20, blank=False, null=False, unique=True
    )
    name = models.CharField("Полное наименование", max_length=500, blank=False, null=True)
    short_name = models.CharField("Сокращенное наименование", max_length=125, blank=False, null=True)
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

    class Meta:
        verbose_name = "Школа"
        verbose_name_plural = "Школы"

    def __str__(self):
        if self.school_type is None:
            return self.short_name
        elif self.number is None:
            return f"{self.school_type} ({self.city})"
        return f"{self.school_type} №{self.number} ({self.city})"