# Generated by Django 5.0.4 on 2024-10-25 05:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0019_alter_school_name_alter_school_short_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='school',
            name='ed_level',
            field=models.CharField(blank=True, choices=[('A', '1 — 11 классы'), ('M', '1 — 9 классы'), ('S', '1 — 4 классы'), ('G', '10 — 11 классы'), ('MG', '5 — 11 классы')], max_length=4, null=True, verbose_name='Уровень образования'),
        ),
    ]
