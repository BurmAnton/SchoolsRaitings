# Generated by Django 5.0.4 on 2024-05-06 07:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='group',
            options={'verbose_name': 'группа', 'verbose_name_plural': 'группы'},
        ),
        migrations.AlterModelOptions(
            name='permission',
            options={'verbose_name': 'разрешение', 'verbose_name_plural': 'разрешения'},
        ),
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'пользователь', 'verbose_name_plural': 'пользователи'},
        ),
    ]