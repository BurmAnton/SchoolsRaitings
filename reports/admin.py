from django.contrib import admin
from tinymce.models import HTMLField
from easy_select2 import select2_modelform
from django_admin_listfilter_dropdown.filters import (
    RelatedDropdownFilter, ChoiceDropdownFilter, DropdownFilter, 
)
from django.db.models import Sum
from reports.utils import select_range_option, count_points, count_section_points
from reports.models import SectionSreport
from django.db import transaction
import logging
from datetime import timedelta
from django.utils import timezone

from .models import (
    Attachment, RangeOption, OptionCombination,
    Report, ReportFile, ReportLink, Section, Field, Option, SchoolReport, update_school_report_points, Answer,
    Year
)

from .admin_utils import ColumnWidthMixin, add_custom_admin_css

SectionForm = select2_modelform(Section, attrs={'width': '500px'})

class SectionInline(admin.StackedInline):
    fields = ['number', 'name', 'fields', 'yellow_zone_min', 'green_zone_min']
    filter_horizontal = ['fields',]
    ordering = ('id',)

    model = Section
    def get_extra(self, request, obj=None, **kwargs):
        if obj: return 0
        return 1


@admin.register(Report)
@add_custom_admin_css
class ReportAdmin(ColumnWidthMixin, admin.ModelAdmin):
    list_display = ['id', 'year', 'closter_name', 'ed_level', 'name', 'points', 'is_published']
    list_filter = [
        ('year', DropdownFilter),
        ('closter', RelatedDropdownFilter),
        ('ed_level', ChoiceDropdownFilter),
        'is_published'
    ]
    readonly_fields = ['points',]
    inlines = [SectionInline, ]

    # Настройки ширины столбцов
    column_width_settings = {
        'id': 'column-width-xs column-align-center',
        'year': 'column-width-xs column-align-center',
        'closter_name': 'column-width-md',
        'ed_level': 'column-width-sm column-align-center',
        'name': 'column-width-lg column-truncate',
        'points': 'column-width-xs column-align-center',
        'is_published': 'column-width-sm column-align-center',
    }
    def closter_name(self, obj):
        """Получает название кластера отчета"""
        if obj.closter:
            return obj.closter.name
        return "—"
    closter_name.short_description = "Кластер"

    class Media:
        js = ('admin/js/column_width.js',)

    actions = ['duplicate_report']

    def duplicate_report(self, request, queryset):
        for report in queryset:
            # Create new report
            new_report = Report.objects.create(
                name=f"Copy of {report.name}",
                year=report.year,
                closter=report.closter,
                ed_level=report.ed_level,
                yellow_zone_min=report.yellow_zone_min,
                green_zone_min=report.green_zone_min,
                is_published=False,
                is_counting=report.is_counting,
            )

            # Copy sections
            for section in report.sections.all().order_by('number'):
                new_section = Section.objects.create(
                    report=new_report,
                    name=section.name,
                    number=section.number,
                    yellow_zone_min=section.yellow_zone_min,
                    green_zone_min=section.green_zone_min
                )
                new_section.fields.set(section.fields.all())

    duplicate_report.short_description = "Создать копию выбранных отчетов"

    def has_change_permission(self, request, obj=None):
        # Check if the year's status is 'completed'
        if obj and obj.year.status == 'completed':
            return False
        return super().has_change_permission(request, obj)
        
    def has_delete_permission(self, request, obj=None):
        # Check if the year's status is 'completed'
        if obj and obj.year.status == 'completed':
            return False
        return super().has_delete_permission(request, obj)


# @admin.register(ReportFile)
# class ReportFileAdmin(admin.ModelAdmin):
#     pass


class OptionInline(admin.TabularInline):
    model = Option
    fields = ['number', 'name', 'points', 'zone']
    
    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 3
        return 1
    
    def get_fields(self, request, obj=None):
        # Если показатель имеет тип MULT (множественный выбор), скрываем поле zone
        if obj and obj.answer_type == 'MULT':
            return ['number', 'name', 'points']
        return ['number', 'name', 'points', 'zone']


class RangeOptionInline(admin.TabularInline):
    model = RangeOption
    fields = ['zone', 'range_type',  'greater_or_equal', 'less_or_equal', 'points']
    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 3
        return 1


class CombinationInline(admin.TabularInline):
    model = OptionCombination
    fields = ['option_numbers', 'points']
    
    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 3
        return 1
    
    def get_queryset(self, request):
        # Возвращаем пустой QuerySet по умолчанию
        qs = super().get_queryset(request)
        # Получаем текущий объект Field
        obj_id = request.resolver_match.kwargs.get('object_id')
        if obj_id:
            try:
                field = Field.objects.get(id=obj_id)
                # Если тип ответа не множественный выбор, возвращаем пустой QuerySet
                if field.answer_type != 'MULT':
                    return qs.none()
            except Field.DoesNotExist:
                pass
        return qs


@admin.register(Field)
@add_custom_admin_css
class FieldAdmin(ColumnWidthMixin, admin.ModelAdmin):
    list_display = ['id', 'number', 'name', 'answer_type', 'points',]
    search_fields = ['number', 'name', 'id']
    readonly_fields = ['points',]
    fieldsets = [
        (None, {
            'fields': ['number', 'name', 'answer_type']
        }),
        ('Баллы и зоны', {
            'fields': ['points', 'bool_points', 'max_points', 'yellow_zone_min', 'green_zone_min'],
        }),
        ('Дополнительно', {
            'fields': ['attachment_name', 'attachment_type', 'note'],
        }),
    ]
    
    # Настройки ширины столбцов
    column_width_settings = {
        'id': 'column-width-xs column-align-center',
        'number': 'column-width-sm column-align-center',
        'name': 'column-width-xl column-truncate',
        'answer_type': 'column-width-xl column-align-center',
        'points': 'column-width-xs column-align-center',
        'yellow_zone_min': 'column-width-md column-align-center',
        'green_zone_min': 'column-width-md column-align-center',
    }

    content = HTMLField()

    inlines = [OptionInline, RangeOptionInline, CombinationInline]
    
    actions = ['recalculate_reports']
    
    def recalculate_reports(self, request, queryset):
        """Пересчитать баллы и зоны для всех отчетов, содержащих выбранные показатели"""
        recalculated_fields = 0
        recalculated_answers = 0
        recalculated_reports = 0
        
        with transaction.atomic():
            for field in queryset:
                logger.info(f"Processing field {field.id} '{field.name}'")
                recalculated_fields += 1
                
                # Получаем все затронутые отчеты и школы
                affected_reports = Report.objects.filter(sections__fields=field)
                affected_schools = School.objects.filter(reports__report__in=affected_reports, is_archived=False).distinct()
                
                # Обновляем максимальное количество баллов показателя
                field_points = calculate_field_points(field)
                Field.objects.filter(pk=field.pk).update(points=field_points)
                
                # Перебираем все отчеты школ с этим показателем
                for school in affected_schools:
                    school_reports = SchoolReport.objects.filter(
                        school=school,
                        report__in=affected_reports
                    )
                    
                    for sr in school_reports:
                        recalculated_reports += 1
                        
                        # Получаем все ответы с этим показателем
                        answers = Answer.objects.filter(question=field, s_report=sr)
                        for answer in answers:
                            old_points = answer.points
                            old_zone = answer.zone
                            
                            # Для MULT обрабатываем особым образом
                            if field.answer_type == 'MULT':
                                selected_options = answer.selected_options.all()
                                if selected_options:
                                    option_numbers = sorted([str(opt.number) for opt in selected_options])
                                    option_numbers_str = ','.join(option_numbers)
                                    
                                    # Проверяем комбинации
                                    try:
                                        combination = OptionCombination.objects.get(
                                            field=field, 
                                            option_numbers=option_numbers_str
                                        )
                                        answer.points = combination.points
                                    except OptionCombination.DoesNotExist:
                                        # Суммируем баллы опций
                                        total_points = sum(opt.points for opt in selected_options)
                                        if field.max_points is not None and total_points > field.max_points:
                                            total_points = field.max_points
                                        answer.points = total_points
                                    
                                    # Определяем зону
                                    if field.yellow_zone_min is not None and field.green_zone_min is not None:
                                        if answer.points < field.yellow_zone_min:
                                            answer.zone = 'R'
                                        elif answer.points >= field.green_zone_min:
                                            answer.zone = 'G'
                                        else:
                                            answer.zone = 'Y'
                                    else:
                                        # Проверяем раздел
                                        section = field.sections.first()
                                        if section and section.yellow_zone_min is not None and section.green_zone_min is not None:
                                            if answer.points < section.yellow_zone_min:
                                                answer.zone = 'R'
                                            elif answer.points >= section.green_zone_min:
                                                answer.zone = 'G'
                                            else:
                                                answer.zone = 'Y'
                                        else:
                                            # Простая логика по умолчанию
                                            answer.zone = 'G' if answer.points > 0 else 'R'
                            
                            if old_points != answer.points or old_zone != answer.zone:
                                answer.save()
                                recalculated_answers += 1
                        
                        # Пересчитываем баллы и зону отчета
                        update_school_report_points(sr)
                    
                    # Инвалидируем кэш
                    invalidate_caches_for_report(affected_reports.first().year, school)
        
        message = f"Пересчитано {recalculated_fields} показателей:\n"
        message += f"- Обновлено {recalculated_answers} ответов\n"
        message += f"- Затронуто {recalculated_reports} отчетов"
        self.message_user(request, message)
        logger.info(message)
    
    recalculate_reports.short_description = "Пересчитать баллы и зоны для всех отчетов"
    
    # def get_inline_instances(self, request, obj=None):
    #     inline_instances = super().get_inline_instances(request, obj)
    #     # При создании нового объекта (obj is None) — не показываем CombinationInline
    #     if obj is None or (obj and obj.answer_type != 'MULT'):
    #         inline_instances = [
    #             inline for inline in inline_instances 
    #             if not isinstance(inline, CombinationInline)
    #         ]
    #     return inline_instances

    class Media:
        js = ["../static/admin/js/question_change.js", 'admin/js/column_width.js']

    def has_change_permission(self, request, obj=None):
        # For fields we need to check if any associated section's report year is completed
        if obj:
            for section in obj.sections.all():
                if section.report.year.status == 'completed':
                    return False
        return super().has_change_permission(request, obj)
        
    def has_delete_permission(self, request, obj=None):
        # For fields we need to check if any associated section's report year is completed
        if obj:
            for section in obj.sections.all():
                if section.report.year.status == 'completed':
                    return False
        return super().has_delete_permission(request, obj)


class ReportFileInline(admin.TabularInline):
    model = ReportFile
    fields = ['file', 'answer']


class LinkInline(admin.TabularInline):
    model = ReportLink
    fields = ['link', 'answer']


logger = logging.getLogger(__name__)

@admin.register(SchoolReport)
@add_custom_admin_css
class SchoolReportAdmin(ColumnWidthMixin, admin.ModelAdmin):
    list_display = ['id', 'school', 'report_name', 'report_closter', 'report_ed_level', 'status', 'points', 'zone', 'is_marked_for_deletion', 'deletion_date']
    list_filter = [
        'status', 
        'zone', 
        'is_marked_for_deletion',
        ('school__closter', RelatedDropdownFilter),
        ('school__ed_level', ChoiceDropdownFilter),
    ]
    search_fields = ['school__name', 'report__name']
    readonly_fields = ['points', 'zone']

    actions = ['recalculate_points_and_zones', 'mark_for_deletion_30_days', 'mark_for_deletion_7_days', 'mark_for_deletion_5_minutes', 'unmark_deletion']
    
    # Настройки ширины столбцов
    column_width_settings = {
        'id': 'column-width-xs column-align-center',
        'school': 'column-width-lg column-truncate',
        'report_name': 'column-width-lg column-truncate',
        'report_closter': 'column-width-md column-truncate',
        'report_ed_level': 'column-width-sm column-align-center',
        'status': 'column-width-sm column-align-center',
        'points': 'column-width-xs column-align-center',
        'zone': 'column-width-xs column-align-center',
        'is_marked_for_deletion': 'column-width-sm column-align-center',
        'deletion_date': 'column-width-md column-align-center',
    }
    
    class Media:
        js = ('admin/js/column_width.js',)
    
    def get_queryset(self, request):
        """Переопределяем метод, чтобы использовать admin_objects вместо objects"""
        return SchoolReport.admin_objects.all()

    def report_name(self, obj):
        """Получает название отчета"""
        if obj.report:
            return obj.report.name
        return "—"
    report_name.short_description = "Название отчета"

    def report_closter(self, obj):
        """Получает кластер школы для отчета"""
        if obj.school and obj.school.closter:
            return obj.school.closter
        return "—"
    report_closter.short_description = "Кластер"
    
    def report_ed_level(self, obj):
        """Получает уровень образования школы для отчета"""
        if obj.school and obj.school.ed_level:
            # Преобразуем код уровня образования в читаемый текст
            choices_dict = dict(obj.school.SCHOOL_LEVELS)
            return choices_dict.get(obj.school.ed_level, obj.school.ed_level)
        return "—"
    report_ed_level.short_description = "Уровень образования"

    def recalculate_points_and_zones(self, request, queryset):
        """Recalculate all answers, sections, and report points/zones"""
        updated_answers = 0
        updated_sections = 0
        updated_reports = 0

        with transaction.atomic():
            for school_report in queryset:
                logger.info(f"Processing school report {school_report.id} for {school_report.school}")
                
                # Recalculate each answer
                for answer in school_report.answers.select_related('question').all():
                    old_points = answer.points
                    old_zone = answer.zone
                    
                    if answer.question.answer_type == 'LST' and answer.option:
                        answer.points = answer.option.points
                        answer.zone = answer.option.zone
                    elif answer.question.answer_type == 'BL':
                        answer.points = answer.question.bool_points if answer.bool_value else 0
                        answer.zone = 'G' if answer.bool_value else 'R'
                    elif answer.question.answer_type in ['NMBR', 'PRC'] and answer.number_value is not None:
                        r_option = select_range_option(answer.question.range_options.all(), answer.number_value)
                        if r_option:
                            answer.points = r_option.points
                            answer.zone = r_option.zone
                        else:
                            answer.points = 0
                            answer.zone = 'R'
                    elif answer.question.answer_type == 'MULT':
                        # Получаем все выбранные опции
                        selected_options = answer.selected_options.all()
                        if selected_options:
                            # Если есть выбранные опции, проверяем комбинации
                            option_numbers = sorted([str(opt.number) for opt in selected_options])
                            option_numbers_str = ','.join(option_numbers)
                            
                            # Проверяем, есть ли точное совпадение с комбинацией
                            try:
                                combination = OptionCombination.objects.get(
                                    field=answer.question, 
                                    option_numbers=option_numbers_str
                                )
                                answer.points = combination.points
                            except OptionCombination.DoesNotExist:
                                # Если нет точного совпадения, суммируем баллы выбранных опций
                                total_points = sum(opt.points for opt in selected_options)
                                
                                # Проверяем, не превышает ли сумма максимальное значение (если оно задано)
                                if answer.question.max_points is not None and total_points > answer.question.max_points:
                                    total_points = answer.question.max_points
                                    
                                answer.points = total_points
                            
                            # Определяем зону исходя из полученных баллов и настроек показателя
                            field = answer.question
                            if field.yellow_zone_min is not None and field.green_zone_min is not None:
                                if answer.points < field.yellow_zone_min:
                                    answer.zone = 'R'
                                elif answer.points >= field.green_zone_min:
                                    answer.zone = 'G'
                                else:
                                    answer.zone = 'Y'
                            else:
                                # Если зоны не определены, используем красную зону по умолчанию
                                answer.zone = 'R'
                        else:
                            answer.points = 0
                            answer.zone = 'R'
                    else:
                        answer.points = 0
                        answer.zone = 'R'
                        
                    if old_points != answer.points or old_zone != answer.zone:
                        answer.save()
                        updated_answers += 1
                        logger.info(f"Updated answer {answer.id}: points {old_points}->{answer.points}, zone {old_zone}->{answer.zone}")

                # Recalculate each section
                for section_sreport in school_report.sections.select_related('section').all():
                    old_points = section_sreport.points
                    old_zone = section_sreport.zone
                    
                    section_points = Answer.objects.filter(question__in=section_sreport.section.fields.all(), s_report=school_report).aggregate(Sum('points'))['points__sum'] or 0
                    section_sreport.points = section_points
                    if section_points < section_sreport.section.yellow_zone_min:
                        section_sreport.zone = 'R'
                    elif section_points >= section_sreport.section.green_zone_min:
                        section_sreport.zone = 'G'
                    else:
                        section_sreport.zone = 'Y'
                        
                    if old_points != section_sreport.points or old_zone != section_sreport.zone:
                        section_sreport.save()
                        updated_sections += 1
                        logger.info(f"Updated section {section_sreport.id}: points {old_points}->{section_sreport.points}, zone {old_zone}->{section_sreport.zone}")

                # Update school report points and zone
                old_points = school_report.points
                old_zone = school_report.zone
                
                zone, points_sum = count_points(school_report)
                school_report.points = points_sum or 0
                school_report.zone = zone or 'R'
                
                if old_points != school_report.points or old_zone != school_report.zone:
                    school_report.save()
                    updated_reports += 1
                    logger.info(f"Updated report {school_report.id}: points {old_points}->{school_report.points}, zone {old_zone}->{school_report.zone}")

        message = f"Recalculated {queryset.count()} reports:\n"
        message += f"- Updated {updated_answers} answers\n"
        message += f"- Updated {updated_sections} sections\n"
        message += f"- Updated {updated_reports} report totals"
        self.message_user(request, message)
        logger.info(message)

    recalculate_points_and_zones.short_description = "Пересчитать баллы и зоны"

    def mark_for_deletion_30_days(self, request, queryset):
        """Пометить выбранные отчёты на удаление через 30 дней"""
        for school_report in queryset:
            school_report.mark_for_deletion(days=30)
        
        self.message_user(request, f"{queryset.count()} отчетов помечено на удаление через 30 дней.")
    mark_for_deletion_30_days.short_description = "Пометить на удаление через 30 дней"
    
    def mark_for_deletion_7_days(self, request, queryset):
        """Пометить выбранные отчёты на удаление через 7 дней"""
        for school_report in queryset:
            school_report.mark_for_deletion(days=7)
        
        self.message_user(request, f"{queryset.count()} отчетов помечено на удаление через 7 дней.")
    mark_for_deletion_7_days.short_description = "Пометить на удаление через 7 дней"
    
    def mark_for_deletion_5_minutes(self, request, queryset):
        """Пометить выбранные отчёты на удаление через 5 минут (для тестирования)"""
        for school_report in queryset:
            school_report.is_marked_for_deletion = True
            school_report.deletion_date = timezone.now() + timedelta(minutes=5)
            school_report.save(update_fields=['is_marked_for_deletion', 'deletion_date'])
        
        self.message_user(request, f"{queryset.count()} отчетов помечено на удаление через 5 минут.")
    mark_for_deletion_5_minutes.short_description = "Пометить на удаление через 5 минут (ТЕСТ)"
    
    def unmark_deletion(self, request, queryset):
        """Снять пометку на удаление для выбранных отчётов"""
        count = 0
        for school_report in queryset:
            if school_report.is_marked_for_deletion:
                school_report.unmark_deletion()
                count += 1
        
        self.message_user(request, f"Пометка на удаление снята для {count} отчетов.")
    unmark_deletion.short_description = "Снять пометку на удаление"


# @admin.register(ReportLink)
# class ReportLinkAdmin(admin.ModelAdmin):
#     list_display = ['id', 'link', 'answer']
#     list_filter = ['answer']
#     search_fields = ['school_report__school__name', 'school_report__report__name', 'link']


# @admin.register(Attachment)
# class AttachmentAdmin(admin.ModelAdmin):
#     list_display = ['name', 'attachment_type',]
#     list_filter = [
#         ('attachment_type', ChoiceDropdownFilter),
#     ]
#     search_fields = ["name", 'attachment_type']


@admin.register(Year)
class YearAdmin(ColumnWidthMixin, admin.ModelAdmin):
    list_display = ['year', 'status', 'is_current']
    list_editable = ['status', 'is_current']
    search_fields = ['year']
    list_filter = ['status', 'is_current']
    ordering = ['-year']
    
    column_width_settings = {
        'year': 'column-width-sm',
        'status': 'column-width-md',
        'is_current': 'column-width-xs column-align-center',
    }
    
    # Добавляем CSS для админки
    class Media:
        css = {
            'all': ('admin/css/admin.css',)
        }


class SectionAdmin(ColumnWidthMixin, admin.ModelAdmin):
    list_display = ('number', 'name', 'report', 'points')
    list_filter = ['report__year', 'report']
    search_fields = ['number', 'name']
    filter_horizontal = ('fields',)
    
    class Media:
        js = ['admin/js/column_width.js']
    
    def has_change_permission(self, request, obj=None):
        # Check if the section's report year status is 'completed'
        if obj and obj.report.year.status == 'completed':
            return False
        return super().has_change_permission(request, obj)
        
    def has_delete_permission(self, request, obj=None):
        # Check if the section's report year status is 'completed'
        if obj and obj.report.year.status == 'completed':
            return False
        return super().has_delete_permission(request, obj)


admin.site.register(Section, SectionAdmin)


