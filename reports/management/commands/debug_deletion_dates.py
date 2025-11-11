import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from reports.models import SchoolReport
from datetime import timedelta

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Отладка дат удаления отчетов'

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(self.style.SUCCESS(f'Текущее время: {now}'))
        
        # Получаем все отчеты, отмеченные на удаление
        marked_reports = SchoolReport.all_objects.filter(is_marked_for_deletion=True)
        self.stdout.write(self.style.SUCCESS(f'Всего отчетов, отмеченных на удаление: {marked_reports.count()}'))
        
        # Проверяем, какие из них должны быть удалены уже сейчас
        expired_reports = SchoolReport.all_objects.filter(
            is_marked_for_deletion=True, 
            deletion_date__lte=now
        )
        self.stdout.write(self.style.SUCCESS(f'Отчетов с истекшим сроком: {expired_reports.count()}'))
        
        # Вывод подробной информации
        for report in marked_reports:
            time_diff = report.deletion_date - now
            status = "ПРОСРОЧЕН" if time_diff.total_seconds() <= 0 else f"Осталось {time_diff}"
            
            # Проверяем, найден ли отчет через фильтр истекших сроков
            is_found_as_expired = report.id in [r.id for r in expired_reports]
            expire_check = "НАЙДЕН как просроченный" if is_found_as_expired else "НЕ найден как просроченный"
            
            self.stdout.write(self.style.SUCCESS(
                f'ID: {report.id}\n'
                f'- Дата удаления: {report.deletion_date}\n'
                f'- Текущее время: {now}\n'
                f'- Статус: {status}\n'
                f'- Проверка: {expire_check}'
            ))
            
        # Для отладки временно пометим один отчет на удаление с датой в прошлом
        self.stdout.write(self.style.WARNING(f'\nСоздаем тестовый отчет для удаления'))
        
        report = SchoolReport.objects.first()
        if report:
            past_time = now - timedelta(minutes=5)  # 5 минут назад
            report.is_marked_for_deletion = True
            report.deletion_date = past_time
            report.save(update_fields=['is_marked_for_deletion', 'deletion_date'])
            
            self.stdout.write(self.style.SUCCESS(
                f'Отчет ID: {report.id} помечен на удаление с датой в прошлом: {past_time}\n'
                f'Разница с текущим временем: {now - past_time}'
            ))
            
            # Проверяем еще раз фильтр
            expired_reports = SchoolReport.all_objects.filter(
                is_marked_for_deletion=True, 
                deletion_date__lte=now
            )
            self.stdout.write(self.style.SUCCESS(f'Отчетов с истекшим сроком после изменения: {expired_reports.count()}'))
            
            for exp_report in expired_reports:
                self.stdout.write(self.style.SUCCESS(
                    f'Просроченный отчет ID: {exp_report.id}, Дата удаления: {exp_report.deletion_date}'
                ))
        else:
            self.stdout.write(self.style.ERROR('Нет доступных отчетов для тестирования')) 