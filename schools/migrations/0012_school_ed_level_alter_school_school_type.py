# Generated by Django 5.0.4 on 2024-06-22 15:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0011_remove_school_inn_school_ais_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='school',
            name='ed_level',
            field=models.CharField(blank=True, choices=[('A', '1 — 11 классы'), ('M', '1 — 9 классы'), ('S', '1 — 4 классы'), ('G', '10 — 11 классы'), ('MG', '5 — 11 классы')], max_length=2, null=True, verbose_name='Уровень образования'),
        ),
        migrations.AlterField(
            model_name='school',
            name='school_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='schools', to='schools.schooltype', verbose_name='Тип школы'),
        ),
    ]
