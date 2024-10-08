# Generated by Django 4.2.6 on 2024-07-10 12:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0032_section_note'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=750, verbose_name='Название вложения')),
                ('attachment_type', models.CharField(blank=True, choices=[('DC', 'Документ (прикреплённый файл)'), ('LNK', 'Ссылка')], max_length=3, null=True, verbose_name='Цель обучения')),
            ],
            options={
                'verbose_name': 'Вложение',
                'verbose_name_plural': 'Вложения',
            },
        ),
    ]
