import logging
from django.core.management.base import BaseCommand
from reports.models import SchoolReport

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Тестирует фильтрацию отчетов, отмеченных на удаление'

    def handle(self, *args, **options):
        # Получаем все отчеты через all_objects (включая помеченные на удаление)
        all_reports_count = SchoolReport.all_objects.count()
        
        # Получаем только активные отчеты через objects (исключая помеченные на удаление)
        active_reports_count = SchoolReport.objects.count()
        
        # Получаем отчеты, помеченные на удаление
        deleted_reports_count = SchoolReport.all_objects.filter(is_marked_for_deletion=True).count()
        
        # Проверяем, что сумма активных и удаленных отчетов равна общему количеству
        is_correct = (active_reports_count + deleted_reports_count) == all_reports_count
        
        self.stdout.write(self.style.SUCCESS(f'Всего отчетов: {all_reports_count}'))
        self.stdout.write(self.style.SUCCESS(f'Активных отчетов: {active_reports_count}'))
        self.stdout.write(self.style.SUCCESS(f'Отчетов, помеченных на удаление: {deleted_reports_count}'))
        
        if is_correct:
            self.stdout.write(self.style.SUCCESS('Фильтрация работает корректно!'))
        else:
            self.stdout.write(self.style.ERROR('Ошибка в фильтрации!')) 