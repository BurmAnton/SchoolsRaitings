# Generated by Django 5.0.4 on 2024-10-01 12:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0077_answer_file'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='field',
            options={'ordering': ['number'], 'verbose_name': 'Критерий', 'verbose_name_plural': 'Критерии'},
        ),
        migrations.AddField(
            model_name='answer',
            name='link',
            field=models.CharField(blank=True, max_length=1500, null=True, verbose_name='Ссылка'),
        ),
        migrations.AlterField(
            model_name='schoolreport',
            name='zone',
            field=models.CharField(choices=[('R', 'Красная'), ('Y', 'Желтая'), ('G', 'Зеленая')], default='R', max_length=5, verbose_name='Зона'),
        ),
    ]