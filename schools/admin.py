from django.contrib import admin
from django_admin_listfilter_dropdown.filters import (
    RelatedDropdownFilter, ChoiceDropdownFilter, DropdownFilter,
)

from .models import TerAdmin, SchoolType, School, SchoolCloster, QuestionCategory, Question


# Register your models here.
@admin.register(TerAdmin)
class TerAdminAdmin(admin.ModelAdmin):
    search_fields = ['name', ]
    list_display = ['name', 'representative']
    autocomplete_fields = ['representative', ]


@admin.register(SchoolCloster)
class SchoolClosterAdmin(admin.ModelAdmin):
    pass


@admin.register(SchoolType)
class SchoolTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name')
    


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'number',
        '__str__', 
        'ter_admin',
        'closter',
        'ed_level', 
        'principal',
        
    ]
    autocomplete_fields = ['principal', 'ter_admin', ]
    search_fields = [
        "ais_id", "name", "short_name",
        "email", "city", "number",
    ]
    list_filter = [
        ('ed_level', ChoiceDropdownFilter),
        ('school_type', RelatedDropdownFilter),
        ('ter_admin', RelatedDropdownFilter),
        ('closter', RelatedDropdownFilter),
    ]

@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    pass

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['category', 'short_question', 'created_at']
    list_filter = [
        ('category', RelatedDropdownFilter), 
        'is_resolved',
        'is_visible',
    ]