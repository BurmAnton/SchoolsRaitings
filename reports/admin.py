from django.contrib import admin
from tinymce.models import HTMLField
from easy_select2 import select2_modelform
from django_admin_listfilter_dropdown.filters import (
    RelatedDropdownFilter, ChoiceDropdownFilter, DropdownFilter
)

from .models import (
    Attachment, Question, RangeOption, 
    Report, ReportFile, Section, Field, Option, SchoolReport
)
    
SectionForm = select2_modelform(Section, attrs={'width': '500px'})

class SectionInline(admin.StackedInline):
    #form = SectionForm
    fields = ['number', 'name', 'fields', 'yellow_zone_min', 'green_zone_min']
    filter_horizontal = ['fields',]
    model = Section
    def get_extra(self, request, obj=None, **kwargs):
        if obj: return 0
        return 1


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
    inlines = [SectionInline, ]


@admin.register(ReportFile)
class ReportFileAdmin(admin.ModelAdmin):
    pass


#@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'number', ]
    search_fields = ['number', 'name']

    readonly_fields = ['points',]
    filter_horizontal = ['fields',]
    content = HTMLField()


QuestionForm = select2_modelform(Question, attrs={'width': '500px'})

class QuestionInline(admin.TabularInline):
    model = Question
    form = QuestionForm
    fields = ['name', 'answer_type', ]

    def get_extra(self, request, obj=None, **kwargs):
        if obj: return 1
        return 1



@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'number', 'id']
    search_fields = ['number', 'name', 'id']
    readonly_fields = ['points',]

    inlines = [QuestionInline, ]

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

@admin.register(SchoolReport)
class SchoolReportAdmin(admin.ModelAdmin):
    pass



@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'attachment_type',]
    list_filter = [
        ('attachment_type', ChoiceDropdownFilter),
    ]
    search_fields = ["name", 'attachment_type']


QuestionForm = select2_modelform(Question, attrs={'width': '500px'})

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form=QuestionForm
    list_display = ['name', 'answer_type', 'field']
    list_filter = [
        ('answer_type', ChoiceDropdownFilter),
        ('field', RelatedDropdownFilter),
    ]
    search_fields = ['field__name', 'field__number', 'name', 'answer_type', 'field__id']
    inlines = [OptionInline, RangeOptionInline]

    content = HTMLField()

    class Media:
        js = ["../static/admin/js/question_change.js",]

