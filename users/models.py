from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager

from tinymce import models as tinymce_models

# Create your models here.
class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    username = None
    middle_name = models.CharField("Отчество", max_length=30, blank=True, null=True)
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField("Номер телефона", max_length=20, blank=True, null=True)
    
    objects = CustomUserManager()

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def __str__(self):
        if self.last_name == "":
            return self.email
        if self.middle_name is None or self.middle_name == "":
            return f"{self.last_name} {self.first_name}"
        return f"{self.last_name} {self.first_name} {self.middle_name}"


class Group(Group):
    
    class Meta:
        verbose_name = "группа"
        verbose_name_plural = "группы"


class Permission(Permission):
    
    class Meta:
        verbose_name = "разрешение"
        verbose_name_plural = "разрешения"


    

class Notification(models.Model):
    is_read = models.BooleanField(default=False)
    message = models.TextField()
    link = models.CharField("Ссылка", max_length=700, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"

    def __str__(self):
        return  f'{self.user} ({self.timestamp})'



class MainPageArticle(models.Model):
    header = models.CharField("Название", max_length=750)
    note_for_school = tinymce_models.HTMLField(
        "Текст на стартовую для школ", null=True, blank=True, default=None
    )
    note_for_teradmin = tinymce_models.HTMLField(
        "Текст на главную для ТУ/ДО", null=True, blank=True, default=None
    )
    note_for_min = tinymce_models.HTMLField(
        "Текст на главную для МинОбр", null=True, blank=True, default=None
    )

    class Meta:
        verbose_name = "Стартовая"
        verbose_name_plural = "Стартовая"

    def __str__(self):
        return  f'{self.header}'


class Documentation(models.Model):
    header = models.CharField("Название", max_length=750)
    file = models.FileField("Файл", upload_to='documentation/')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Документация"
        verbose_name_plural = "Документация"

    def __str__(self):
        return  f'{self.header}'