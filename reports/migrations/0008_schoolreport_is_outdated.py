from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0088_schoolreport_deletion_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolreport',
            name='is_outdated',
            field=models.BooleanField(default=False, help_text='Отмечается, если кластер или уровень образования школы изменились после создания отчета', verbose_name='Устаревший отчет'),
        ),
    ] 