# Generated by Django 5.0.4 on 2024-10-08 17:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0079_merge_20241001_1912'),
    ]

    operations = [
        migrations.AlterField(
            model_name='field',
            name='attachment_type',
            field=models.CharField(blank=True, choices=[('DC', 'Документ (прикреплённый файл)'), ('LNK', 'Ссылка'), ('LDC', 'Документ или ссылка'), ('OTH', 'Иной источник (без ссылки/файла)')], default='OTH', max_length=3, null=True, verbose_name='Тип вложения'),
        ),
    ]
