# Generated by Django 5.0.4 on 2024-06-24 07:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0025_rangeoption_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='number_value',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=5, verbose_name='Числовое значение'),
        ),
    ]