# Generated by Django 5.0.4 on 2024-09-12 00:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0056_alter_schoolreport_zone'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='attachment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='reports.attachment', verbose_name='Источник данных'),
        ),
    ]