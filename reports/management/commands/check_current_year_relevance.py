import logging
from django.core.management.base import BaseCommand
from django.db.models import Count
from reports.models import SchoolReport, Year
from schools.models import School
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Проверяет актуальность отчётов текущего года для школ с 2+ отчётами за текущий год'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Запуск без фактического обновления (только вывод информации)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Получаем текущий год
        current_year = Year.objects.filter(is_current=True).first()
        if not current_year:
            self.stdout.write(self.style.ERROR('Текущий год не установлен. Установите is_current=True для одного из годов.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Текущий год: {current_year.year}'))
        
        # Находим школы с 2+ отчётами за текущий год
        # Используем all_objects чтобы учесть все отчёты, включая помеченные на удаление
        schools_with_reports = SchoolReport.all_objects.filter(
            report__year=current_year
        ).values('school').annotate(
            reports_count=Count('id')
        ).filter(reports_count__gte=2).values_list('school', flat=True)
        
        if not schools_with_reports.exists():
            self.stdout.write(self.style.SUCCESS('Нет школ с 2+ отчётами за текущий год'))
            return
        
        schools_count = schools_with_reports.count()
        self.stdout.write(self.style.SUCCESS(f'Найдено школ с 2+ отчётами: {schools_count}'))
        
        outdated_count = 0
        updated_count = 0
        total_reports_checked = 0
        
        if dry_run:
            self.stdout.write(self.style.WARNING('[ТЕСТОВЫЙ ЗАПУСК] Отчёты не будут обновлены'))
        
        self.stdout.write('-' * 80)
        
        with transaction.atomic():
            for school_id in schools_with_reports:
                # Получаем все отчёты текущего года для этой школы
                school_reports = SchoolReport.all_objects.filter(
                    school_id=school_id,
                    report__year=current_year
                ).select_related('report', 'report__year', 'report__closter', 'school', 'school__closter')
                
                school = school_reports.first().school
                # Получаем читаемое название уровня образования
                ed_level_choices = dict(School.SCHOOL_LEVELS)
                ed_level_display = ed_level_choices.get(school.ed_level, school.ed_level)
                
                self.stdout.write(f'\nШкола: {school.name} (ID: {school.id})')
                self.stdout.write(f'  Кластер: {school.closter.name if school.closter else "—"}')
                self.stdout.write(f'  Уровень образования: {ed_level_display}')
                self.stdout.write(f'  Отчётов за текущий год: {school_reports.count()}')
                
                for s_report in school_reports:
                    total_reports_checked += 1
                    was_outdated = s_report.is_outdated
                    
                    if dry_run:
                        # В тестовом режиме просто проверяем, не обновляя
                        report_is_relevant = True
                        if s_report.school.closter != s_report.report.closter:
                            report_is_relevant = False
                        if s_report.school.ed_level != s_report.report.ed_level:
                            report_is_relevant = False
                        
                        will_be_outdated = not report_is_relevant
                        if will_be_outdated != was_outdated:
                            self.stdout.write(self.style.WARNING(
                                f'  - Отчёт ID: {s_report.id}, "{s_report.report.name}" '
                                f'изменит статус: {"устаревший" if was_outdated else "актуальный"} -> '
                                f'{"устаревший" if will_be_outdated else "актуальный"}'
                            ))
                        elif will_be_outdated:
                            self.stdout.write(self.style.WARNING(
                                f'  - Отчёт ID: {s_report.id}, "{s_report.report.name}" - устаревший'
                            ))
                        else:
                            self.stdout.write(f'  - Отчёт ID: {s_report.id}, "{s_report.report.name}" - актуальный')
                    else:
                        # Фактическая проверка и обновление
                        is_relevant = s_report.check_relevance()
                        s_report.refresh_from_db()
                        
                        if s_report.is_outdated:
                            outdated_count += 1
                            if not was_outdated:
                                updated_count += 1
                                self.stdout.write(self.style.WARNING(
                                    f'  - Отчёт ID: {s_report.id}, "{s_report.report.name}" помечен как устаревший'
                                ))
                                logger.info(
                                    f'Отчёт ID: {s_report.id} школы {school.name} помечен как устаревший. '
                                    f'Кластер школы: {school.closter}, кластер отчёта: {s_report.report.closter}. '
                                    f'Уровень школы: {school.ed_level}, уровень отчёта: {s_report.report.ed_level}'
                                )
                            else:
                                self.stdout.write(f'  - Отчёт ID: {s_report.id}, "{s_report.report.name}" - устаревший (уже был помечен)')
                        else:
                            if was_outdated:
                                updated_count += 1
                                self.stdout.write(self.style.SUCCESS(
                                    f'  - Отчёт ID: {s_report.id}, "{s_report.report.name}" помечен как актуальный'
                                ))
                            else:
                                self.stdout.write(f'  - Отчёт ID: {s_report.id}, "{s_report.report.name}" - актуальный')
            
            if dry_run:
                # В тестовом режиме не коммитим транзакцию
                transaction.set_rollback(True)
        
        self.stdout.write('-' * 80)
        self.stdout.write(self.style.SUCCESS(f'\nПроверено отчётов: {total_reports_checked}'))
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'Устаревших отчётов: {outdated_count}'))
            self.stdout.write(self.style.SUCCESS(f'Обновлено статусов: {updated_count}'))
        else:
            self.stdout.write(self.style.WARNING('Это был тестовый запуск. Для фактического обновления запустите без --dry-run'))

