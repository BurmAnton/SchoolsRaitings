from django.contrib import admin
from tinymce.models import HTMLField
from easy_select2 import select2_modelform
from django_admin_listfilter_dropdown.filters import (
    RelatedDropdownFilter, ChoiceDropdownFilter, DropdownFilter
)

from .models import (
    Attachment, Question, RangeOption, Report, ReportFile, 
    SchoolReport, Section, Field, Option,
)

    

class AttachmentInline(admin.TabularInline):
    model = Attachment
    def get_extra(self, request, obj=None, **kwargs):
        if obj: return 0
        return 1


SectionForm = select2_modelform(Section, attrs={'width': '500px'})


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name','closter', 'ed_level', 'year']
    list_filter = ['year',]
    list_filter = [
        ('year', DropdownFilter),
        ('closter', RelatedDropdownFilter),
        ('ed_level', ChoiceDropdownFilter),
        'is_published'
    ]
    readonly_fields = ['points',]
    inlines = [AttachmentInline, ]
    filter_horizontal = ['sections', ]


class FieldInline(admin.TabularInline):
    model = Field
    fields = ['number', 'name']


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'number', ]
    list_filter = ['reports', ]
    search_fields = ['number', 'name']
    inlines = [FieldInline, ]
    list_filter = [
        ('reports', RelatedDropdownFilter),
    ]
    readonly_fields = ['points',]

    content = HTMLField()


class QuestionInline(admin.TabularInline):
    model = Question
    fields = ['name', 'answer_type']
    


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ['section', 'number', 'name']
    search_fields = ['section', 'number', 'name']
    readonly_fields = ['points',]

    inlines = [QuestionInline, ]
    list_filter = [
        ('section', RelatedDropdownFilter),
    ]

    content = HTMLField()


class OptionInline(admin.TabularInline):
    model = Option
    fields = ['name', 'points', 'zone',]
    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 0
        return 3


class RangeOptionInline(admin.TabularInline):
    model = RangeOption
    fields = ['zone', 'range_type',  'greater_or_equal', 'less_or_equal', 'equal', 'points']
    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 0
        return 3

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['name', 'answer_type', 'field']
    search_fields = ['field', 'name', 'answer_type']
    inlines = [OptionInline, RangeOptionInline]
    list_filter = [
        ('field__section__reports', RelatedDropdownFilter),
        ('field', RelatedDropdownFilter),
    ]

    content = HTMLField()

    class Media:
        js = ["../static/admin/js/question_change.js",]


class ReportFileInline(admin.TabularInline):
    model = ReportFile
    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 0
        return 3


@admin.register(SchoolReport)
class SchoolReport(admin.ModelAdmin):
    inlines = [ReportFileInline, ]