# Generated by Django 5.0.4 on 2024-11-11 02:49

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0020_alter_school_ed_level'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='teradmin',
            name='representative',
        ),
        migrations.AddField(
            model_name='teradmin',
            name='representatives',
            field=models.ManyToManyField(blank=True, null=True, related_name='ter_admin', to=settings.AUTH_USER_MODEL, verbose_name='Представитель ТУ/ДО'),
        ),
    ]