# Generated by Django 5.0.4 on 2024-09-22 20:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0063_rename_report_field_question_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='is_counting',
            field=models.BooleanField(default=False, verbose_name='Показывать зоны?'),
        ),
        migrations.AlterField(
            model_name='rangeoption',
            name='less_or_equal',
            field=models.DecimalField(blank=True, decimal_places=1, default=None, max_digits=5, null=True, verbose_name='Меньше или равно'),
        ),
        migrations.AlterField(
            model_name='report',
            name='green_zone_min',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, max_digits=5, null=True, verbose_name='Зеленая зона (минимум)'),
        ),
        migrations.AlterField(
            model_name='report',
            name='yellow_zone_min',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, max_digits=5, null=True, verbose_name='Жёлтая зона (минимум)'),
        ),
    ]
