# Generated by Django 5.0.4 on 2025-03-27 09:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0094_update_report_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='field',
            name='green_zone_min',
            field=models.DecimalField(blank=True, decimal_places=1, default=None, max_digits=5, null=True, verbose_name='Зеленая зона (минимум)'),
        ),
        migrations.AddField(
            model_name='field',
            name='yellow_zone_min',
            field=models.DecimalField(blank=True, decimal_places=1, default=None, max_digits=5, null=True, verbose_name='Жёлтая зона (минимум)'),
        ),
    ]
