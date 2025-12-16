import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from reports.models import SchoolReport

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Удаляет отчеты школ, отмеченные на удаление, у которых истек срок'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Запуск без фактического удаления (только вывод информации)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        self.stdout.write(self.style.SUCCESS(f'Текущее время: {now.strftime("%Y-%m-%d %H:%M:%S")}'))
        
        # Получаем все отчеты, отмеченные на удаление, у которых истек срок
        # Используем all_objects вместо objects, чтобы найти отчеты, помеченные на удаление
        try:
            reports_to_delete = SchoolReport.all_objects.filter(
                is_marked_for_deletion=True, 
                deletion_date__lte=now
            )
            
            if not reports_to_delete.exists():
                self.stdout.write(self.style.SUCCESS('Нет отчетов для удаления'))
                # Показываем также отчеты, которые еще ожидают удаления
                pending = SchoolReport.all_objects.filter(is_marked_for_deletion=True).exclude(deletion_date__lte=now)
                if pending.exists():
                    self.stdout.write(self.style.SUCCESS(f'Отчетов, ожидающих удаления: {pending.count()}'))
                return
            
            count = reports_to_delete.count()
            
            if dry_run:
                self.stdout.write(self.style.WARNING(
                    f'[ТЕСТОВЫЙ ЗАПУСК] Найдено {count} отчетов для удаления:'
                ))
                for report in reports_to_delete:
                    self.stdout.write(self.style.WARNING(
                        f'- ID: {report.id}, Школа: {report.school}, Отчет: {report.report}, '
                        f'Дата удаления: {report.deletion_date}'
                    ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'Удаление {count} отчетов...'
                ))
                
                # Логируем информацию о каждом удаляемом отчете
                for report in reports_to_delete:
                    logger.info(
                        f'Удаление отчета ID: {report.id}, Школа: {report.school.name}, '
                        f'Отчет: {report.report.name}, Дата удаления: {report.deletion_date}'
                    )
                    self.stdout.write(f'Удаление отчета ID: {report.id}...')
                
                # Фактическое удаление
                deleted_count, deleted_dict = reports_to_delete.delete()
                
                self.stdout.write(self.style.SUCCESS(
                    f'Успешно удалено {deleted_count} отчетов'
                ))
                if deleted_dict:
                    self.stdout.write(f'Детали удаления: {deleted_dict}')
                    
        except Exception as e:
            error_msg = f'Ошибка при удалении отчетов: {str(e)}'
            logger.error(error_msg, exc_info=True)
            self.stdout.write(self.style.ERROR(error_msg))
            raise 