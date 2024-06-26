from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


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