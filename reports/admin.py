from django.contrib import admin

from .models import Question, RangeOption, Report, SchoolReport, Section, Field, Option


class SectionInline(admin.TabularInline):
    model = Section
    fields = ['number', 'name']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'closter', 'year']
    list_filter = ['closter', 'year']
    inlines = [SectionInline, ]


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
    list_display = ['field', 'name', 'answer_type']
    list_filter = ['field', ]
    search_fields = ['field', 'name', 'answer_type']
    inlines = [OptionInline, RangeOptionInline]

@admin.register(SchoolReport)
class SchoolReport(admin.ModelAdmin):
    pass