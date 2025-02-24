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

from .models import (
    Attachment, RangeOption, 
    Report, ReportFile, ReportLink, Section, Field, Option, SchoolReport, update_school_report_points
)
    
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
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'year', 'closter', 'ed_level', 'name', 'points']
    list_filter = ['year',]
    list_filter = [
        ('year', DropdownFilter),
        ('closter', RelatedDropdownFilter),
        ('ed_level', ChoiceDropdownFilter),
        'is_published'
    ]
    readonly_fields = ['points',]
    inlines = [SectionInline, ]

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


# @admin.register(ReportFile)
# class ReportFileAdmin(admin.ModelAdmin):
#     pass


class OptionInline(admin.TabularInline):
    model = Option
    fields = ['name', 'points', 'zone',]
    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 3
        return 1


class RangeOptionInline(admin.TabularInline):
    model = RangeOption
    fields = ['zone', 'range_type',  'greater_or_equal', 'less_or_equal', 'points']
    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 3
        return 1


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'name']
    search_fields = ['number', 'name', 'id']
    readonly_fields = ['points',]

    content = HTMLField()

    inlines = [OptionInline, RangeOptionInline]

    class Media:
        js = ["../static/admin/js/question_change.js",]



class ReportFileInline(admin.TabularInline):
    model = ReportFile
    fields = ['file', 'answer']


class LinkInline(admin.TabularInline):
    model = ReportLink
    fields = ['link', 'answer']


logger = logging.getLogger(__name__)

@admin.register(SchoolReport)
class SchoolReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'school', 'report', 'status', 'points', 'zone']
    list_filter = ['status', 'zone']
    search_fields = ['school__name', 'report__name']
    readonly_fields = ['points', 'zone']

    actions = ['recalculate_points_and_zones']

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
                    
                    section_points = count_section_points(section_sreport) or 0
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


@admin.register(ReportLink)
class ReportLinkAdmin(admin.ModelAdmin):
    list_display = ['id', 'link', 'answer']
    list_filter = ['answer']
    search_fields = ['school_report__school__name', 'school_report__report__name', 'link']


# @admin.register(Attachment)
# class AttachmentAdmin(admin.ModelAdmin):
#     list_display = ['name', 'attachment_type',]
#     list_filter = [
#         ('attachment_type', ChoiceDropdownFilter),
#     ]
#     search_fields = ["name", 'attachment_type']


