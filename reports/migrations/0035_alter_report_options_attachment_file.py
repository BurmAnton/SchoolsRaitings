# Generated by Django 4.2.6 on 2024-07-10 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0034_attachment_report'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='report',
            options={'verbose_name': 'Отчёт (шаблон)', 'verbose_name_plural': 'Отчёты (шаблон)'},
        ),
        migrations.AddField(
            model_name='attachment',
            name='file',
            field=models.FileField(blank=True, max_length=200, null=True, upload_to='media/attachments/', verbose_name='Файл'),
        ),
    ]