# Generated by Django 5.0.4 on 2025-03-09 11:39

import django.db.models.deletion
from django.db import migrations, models


def link_reports_to_years(apps, schema_editor):
    """
    Связывает существующие отчеты (Report) с соответствующими записями Year
    """
    Report = apps.get_model('reports', 'Report')
    Year = apps.get_model('reports', 'Year')
    
    # Создаем словарь {год: объект_года}
    year_dict = {year_obj.year: year_obj for year_obj in Year.objects.all()}
    
    # Перебираем все отчеты и устанавливаем ссылку year_ref
    for report in Report.objects.all():
        year_value = report.year
        year_obj = year_dict.get(year_value)
        
        # Если не нашли существующий год, создаем новый
        if not year_obj:
            current_year = 2024  # Предполагаем, что текущий год - 2024
            year_obj = Year.objects.create(
                year=year_value,
                status='completed' if year_value < current_year else 'forming',
                is_current=(year_value == current_year)
            )
            year_dict[year_value] = year_obj
            
        # Устанавливаем ссылку
        report.year_ref = year_obj
        report.save(update_fields=['year_ref'])


def unlink_reports_from_years(apps, schema_editor):
    """
    Обратная операция - очищаем ссылки year_ref
    """
    Report = apps.get_model('reports', 'Report')
    Report.objects.all().update(year_ref=None)


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0089_year'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='year_ref',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='reports.year', verbose_name='Год'),
        ),
        migrations.AlterField(
            model_name='report',
            name='year',
            field=models.IntegerField(verbose_name='Год (устаревшее)'),
        ),
        # Выполняем функцию для связывания отчетов с годами
        migrations.RunPython(link_reports_to_years, unlink_reports_from_years),
    ]
