# Generated by Django 5.0.4 on 2024-06-22 13:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0021_alter_reportzone_options'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reportzone',
            name='school_type',
        ),
        migrations.AddField(
            model_name='reportzone',
            name='ed_level',
            field=models.CharField(choices=[('A', '1 — 11 классы'), ('M', '1 — 9 классы'), ('S', '1 — 4 классы'), ('G', '10 — 11 классы'), ('MG', '5 — 11 классы')], default='A', max_length=2, verbose_name='Уровень образования'),
            preserve_default=False,
        ),
    ]
