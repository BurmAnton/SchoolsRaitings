# Generated by Django 5.0.4 on 2024-09-29 17:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0074_field_attachment_name_field_attachment_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='field',
            name='attachment_type',
            field=models.CharField(blank=True, choices=[('DC', 'Документ (прикреплённый файл)'), ('LNK', 'Ссылка'), ('OTH', 'Иной источник (без ссылки/файла)')], default='OTH', max_length=3, null=True, verbose_name='Тип вложения'),
        ),
    ]