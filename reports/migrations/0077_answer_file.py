# Generated by Django 5.0.4 on 2024-09-29 20:59

import reports.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0076_alter_section_options_remove_reportfile_answers_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='file',
            field=models.FileField(blank=True, max_length=200, null=True, upload_to=reports.models.Answer.file_path, verbose_name='Файл'),
        ),
    ]
