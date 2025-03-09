import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from reports.models import SchoolReport
from datetime import timedelta

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Проверяет отчеты, отмеченные на удаление, и показывает оставшееся время'

    def handle(self, *args, **options):
        now = timezone.now()
        marked_reports = SchoolReport.all_objects.filter(is_marked_for_deletion=True)
        
        if not marked_reports.exists():
            self.stdout.write(self.style.SUCCESS('Нет отчетов, ожидающих удаления'))
            return
            
        self.stdout.write(self.style.SUCCESS(f'Найдено {marked_reports.count()} отчетов, отмеченных на удаление:'))
        self.stdout.write('-' * 80)
        
        for i, report in enumerate(marked_reports, 1):
            time_left = report.deletion_date - now if report.deletion_date > now else timedelta(0)
            hours, remainder = divmod(time_left.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            self.stdout.write(self.style.SUCCESS(
                f'{i}. ID: {report.id}, Школа: {report.school.name}, Отчет: {report.report.name}\n'
                f'   Запланировано удаление: {report.deletion_date.strftime("%Y-%m-%d %H:%M:%S")}\n'
                f'   Осталось времени: {int(hours)}ч {int(minutes)}мин {int(seconds)}сек\n'
            ))
            
            # Помечаем отчеты, которые должны быть удалены уже сейчас
            if time_left.total_seconds() <= 0:
                self.stdout.write(self.style.WARNING(f'   ГОТОВ К УДАЛЕНИЮ - запустите команду delete_expired_reports'))
            
        self.stdout.write('-' * 80)
        self.stdout.write(self.style.SUCCESS('Для удаления отчетов с истекшим сроком выполните:'))
        self.stdout.write(self.style.SUCCESS('python manage.py delete_expired_reports'))
        self.stdout.write(self.style.SUCCESS('Для тестового запуска без удаления:'))
        self.stdout.write(self.style.SUCCESS('python manage.py delete_expired_reports --dry-run')) 