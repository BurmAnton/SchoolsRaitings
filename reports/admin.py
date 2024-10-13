from django.contrib import admin
from tinymce.models import HTMLField
from easy_select2 import select2_modelform
from django_admin_listfilter_dropdown.filters import (
    RelatedDropdownFilter, ChoiceDropdownFilter, DropdownFilter, 
)

from .models import (
    Attachment, RangeOption, 
    Report, ReportFile, Section, Field, Option, SchoolReport
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
    list_display = ['id', 'year', 'closter', 'ed_level', 'name']
    list_filter = ['year',]
    list_filter = [
        ('year', DropdownFilter),
        ('closter', RelatedDropdownFilter),
        ('ed_level', ChoiceDropdownFilter),
        'is_published'
    ]
    readonly_fields = ['points',]
    inlines = [SectionInline, ]


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


@admin.register(SchoolReport)
class SchoolReportAdmin(admin.ModelAdmin):
    pass



# @admin.register(Attachment)
# class AttachmentAdmin(admin.ModelAdmin):
#     list_display = ['name', 'attachment_type',]
#     list_filter = [
#         ('attachment_type', ChoiceDropdownFilter),
#     ]
#     search_fields = ["name", 'attachment_type']


