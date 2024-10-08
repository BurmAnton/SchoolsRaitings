# Generated by Django 5.0.4 on 2024-06-16 11:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Option',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, verbose_name='Название')),
                ('points', models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Колво баллов')),
            ],
            options={
                'verbose_name': 'Вариант ответа',
                'verbose_name_plural': 'Варианты ответа',
            },
        ),
        migrations.DeleteModel(
            name='Criterion',
        ),
        migrations.AlterModelOptions(
            name='field',
            options={'verbose_name': 'Показатель', 'verbose_name_plural': 'Показатели'},
        ),
        migrations.AlterModelOptions(
            name='question',
            options={'verbose_name': 'Критерий', 'verbose_name_plural': 'Критерии'},
        ),
        migrations.AddField(
            model_name='question',
            name='answer_type',
            field=models.CharField(choices=[('BL', 'Бинарный выбор (Да/Нет)'), ('NMBR', 'Числовое значение'), ('LST', 'Выбор из списка')], default='BL', max_length=5, verbose_name='Тип ответа'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='question',
            name='bool_points',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Баллы (если бинарный выбор)'),
        ),
        migrations.AddField(
            model_name='question',
            name='name',
            field=models.CharField(blank=True, max_length=750, null=True, verbose_name='Название критерия'),
        ),
        migrations.AlterField(
            model_name='field',
            name='name',
            field=models.CharField(max_length=750, verbose_name='Название раздела'),
        ),
        migrations.AlterField(
            model_name='section',
            name='name',
            field=models.CharField(max_length=500, verbose_name='Название раздела'),
        ),
    ]
