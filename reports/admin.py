from django.contrib import admin

from .models import (
    Question, RangeOption, Report, 
    SchoolReport, Section, Field, Option,
    ReportZone
)


class SectionInline(admin.TabularInline):
    model = Section
    fields = ['number', 'name']
    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 0
        return 1


class ReportZoneInline(admin.TabularInline):
    model = ReportZone
    fields = [
        'closter', 'zone', 'ed_level',
        'range_type', 'greater_or_equal', 'less_or_equal'
    ]
    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return 0
        return 1


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'year']
    list_filter = ['year',]
    inlines = [SectionInline, ReportZoneInline]


class FieldInline(admin.TabularInline):
    model = Field
    fields = ['number', 'name']


@admin.register(Section)
class TerAdminAdmin(admin.ModelAdmin):
    list_display = ['report', 'number', 'name']
    list_filter = ['report', ]
    search_fields = ['report', 'number', 'name']
    inlines = [FieldInline, ]


class QuestionInline(admin.TabularInline):
    model = Question
    fields = ['name', 'answer_type']


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ['section', 'number', 'name']
    list_filter = ['section', ]
    search_fields = ['section', 'number', 'name']
    inlines = [QuestionInline, ]


class OptionInline(admin.TabularInline):
    model = Option
    fields = ['name', 'points']


class RangeOptionInline(admin.TabularInline):
    model = RangeOption
    fields = ['range_type', 'less_or_equal', 'greater_or_equal', 'equal']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['name', 'answer_type', 'field']
    list_filter = ['field', ]
    search_fields = ['field', 'name', 'answer_type']
    inlines = [OptionInline, RangeOptionInline]

@admin.register(SchoolReport)
class SchoolReport(admin.ModelAdmin):
    pass