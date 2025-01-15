from django.contrib import admin
from tinymce.models import HTMLField
from easy_select2 import select2_modelform
from django_admin_listfilter_dropdown.filters import (
    RelatedDropdownFilter, ChoiceDropdownFilter, DropdownFilter, 
)

from .models import (
    Attachment, RangeOption, 
    Report, ReportFile, ReportLink, Section, Field, Option, SchoolReport
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


@admin.register(SchoolReport)
class SchoolReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'school', 'report', 'status', 'points', 'zone']
    list_filter = ['status', 'zone']
    search_fields = ['school__name', 'report__name']
    readonly_fields = ['points', 'zone']

    inlines = [ReportFileInline]


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


