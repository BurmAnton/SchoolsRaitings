# Generated by Django 4.2.6 on 2024-07-28 21:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0040_report_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='is_mod_by_mo',
            field=models.BooleanField(default=False, verbose_name='Изменён МинОбром?'),
        ),
    ]