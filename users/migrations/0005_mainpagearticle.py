# Generated by Django 5.0.4 on 2024-09-12 04:12

import tinymce.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_notification_link'),
    ]

    operations = [
        migrations.CreateModel(
            name='MainPageArticle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('header', models.CharField(max_length=750, verbose_name='Заголовок')),
                ('note_for_school', tinymce.models.HTMLField(blank=True, default=None, null=True, verbose_name='Текст на стартовую для школ')),
                ('note_for_teradmin', tinymce.models.HTMLField(blank=True, default=None, null=True, verbose_name='Текст на главную для ТУ/ДО')),
                ('note_for_min', tinymce.models.HTMLField(blank=True, default=None, null=True, verbose_name='Текст на главную для МинОбр')),
            ],
            options={
                'verbose_name': 'Стартовая',
                'verbose_name_plural': 'Стартовая',
            },
        ),
    ]
