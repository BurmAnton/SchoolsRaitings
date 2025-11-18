# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0024_school_is_archived'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='question',
            options={'ordering': ['-created_at'], 'verbose_name': 'Вопрос', 'verbose_name_plural': 'Вопросы'},
        ),
    ]

