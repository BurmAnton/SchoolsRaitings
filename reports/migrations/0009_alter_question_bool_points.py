# Generated by Django 5.0.4 on 2024-06-17 07:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0008_alter_option_points_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='bool_points',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=5, verbose_name='Баллы (если бинарный выбор)'),
        ),
    ]