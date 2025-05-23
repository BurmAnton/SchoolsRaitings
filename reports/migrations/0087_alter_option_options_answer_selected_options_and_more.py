# Generated by Django 5.0.4 on 2025-03-08 14:35

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0086_alter_sectionsreport_section'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='option',
            options={'ordering': ['number'], 'verbose_name': 'Вариант ответа', 'verbose_name_plural': 'Варианты ответа'},
        ),
        migrations.AddField(
            model_name='answer',
            name='selected_options',
            field=models.ManyToManyField(blank=True, related_name='multiple_answers', to='reports.option', verbose_name='выбранные опции'),
        ),
        migrations.AddField(
            model_name='field',
            name='max_points',
            field=models.DecimalField(blank=True, decimal_places=1, default=None, max_digits=5, null=True, verbose_name='Макс. баллов (для множественного выбора)'),
        ),
        migrations.AddField(
            model_name='option',
            name='number',
            field=models.IntegerField(default=0, verbose_name='Номер'),
        ),
        migrations.AlterField(
            model_name='answer',
            name='option',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='reports.option', verbose_name='опция'),
        ),
        migrations.AlterField(
            model_name='field',
            name='answer_type',
            field=models.CharField(choices=[('BL', 'Бинарный выбор (Да/Нет)'), ('LST', 'Выбор из списка'), ('NMBR', 'Числовое значение'), ('PRC', 'Процент'), ('MULT', 'Множественный выбор')], max_length=5, verbose_name='Тип ответа'),
        ),
        migrations.CreateModel(
            name='OptionCombination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('option_numbers', models.CharField(max_length=255, verbose_name='Номера полей (через запятую)')),
                ('points', models.DecimalField(decimal_places=1, default=0, max_digits=5, verbose_name='Количество баллов')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='combinations', to='reports.field', verbose_name='показатель')),
            ],
            options={
                'verbose_name': 'Комбинация вариантов',
                'verbose_name_plural': 'Комбинации вариантов',
            },
        ),
    ]
