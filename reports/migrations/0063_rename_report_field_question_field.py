# Generated by Django 5.0.4 on 2024-09-22 19:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0062_rename_field_question_report_field'),
    ]

    operations = [
        migrations.RenameField(
            model_name='question',
            old_name='report_field',
            new_name='field',
        ),
    ]