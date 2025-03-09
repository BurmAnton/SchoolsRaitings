import logging
from django.core.management.base import BaseCommand
from reports.models import SchoolReport
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Тестирует пометку отчета на удаление и проверку видимости'

    def add_arguments(self, parser):
        parser.add_argument(
            '--revert',
            action='store_true',
            dest='revert',
            default=False,
            help='Снять пометку на удаление с первого отчета',
        )
        parser.add_argument(
            '--minutes',
            action='store',
            dest='minutes',
            type=int,
            default=5,
            help='Количество минут до удаления (по умолчанию 5)',
        )

    def handle(self, *args, **options):
        revert = options['revert']
        minutes = options['minutes']
        
        if revert:
            # Находим первый отчет, помеченный на удаление
            report = SchoolReport.all_objects.filter(is_marked_for_deletion=True).first()
            if report:
                self.stdout.write(self.style.WARNING(f'Снимаем пометку на удаление с отчета школы {report.school.name}'))
                report.unmark_deletion()
                self.stdout.write(self.style.SUCCESS('Пометка на удаление снята'))
            else:
                self.stdout.write(self.style.WARNING('Нет отчетов, помеченных на удаление'))
        else:
            # Проверяем количество отчетов до пометки
            self.stdout.write(self.style.SUCCESS(f'До пометки:'))
            self.stdout.write(self.style.SUCCESS(f'- Всего отчетов (all_objects): {SchoolReport.all_objects.count()}'))
            self.stdout.write(self.style.SUCCESS(f'- Активных отчетов (objects): {SchoolReport.objects.count()}'))
            
            # Находим первый отчет и помечаем его на удаление
            report = SchoolReport.objects.first()
            if report:
                self.stdout.write(self.style.WARNING(f'Помечаем отчет школы {report.school.name} на удаление через {minutes} минут'))
                # Используем minutes вместо дней
                report.is_marked_for_deletion = True
                report.deletion_date = timezone.now() + timedelta(minutes=minutes)
                report.save(update_fields=['is_marked_for_deletion', 'deletion_date'])
                
                # Проверяем количество отчетов после пометки
                self.stdout.write(self.style.SUCCESS(f'После пометки:'))
                self.stdout.write(self.style.SUCCESS(f'- Всего отчетов (all_objects): {SchoolReport.all_objects.count()}'))
                self.stdout.write(self.style.SUCCESS(f'- Активных отчетов (objects): {SchoolReport.objects.count()}'))
                self.stdout.write(self.style.SUCCESS(f'- Отчет будет удален: {report.deletion_date.strftime("%Y-%m-%d %H:%M:%S")}'))
                
                # Проверяем, что отчет не находится через objects
                marked_report = SchoolReport.objects.filter(id=report.id).first()
                if marked_report is None:
                    self.stdout.write(self.style.SUCCESS('Тест пройден: отчет не виден через objects'))
                else:
                    self.stdout.write(self.style.ERROR('Тест не пройден: отчет все еще виден через objects!'))
                
                # Проверяем, что отчет находится через all_objects
                marked_report = SchoolReport.all_objects.filter(id=report.id).first()
                if marked_report is not None:
                    self.stdout.write(self.style.SUCCESS('Тест пройден: отчет виден через all_objects'))
                else:
                    self.stdout.write(self.style.ERROR('Тест не пройден: отчет не виден через all_objects!'))
            else:
                self.stdout.write(self.style.ERROR('Нет доступных отчетов для тестирования')) 