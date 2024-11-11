from django.contrib import admin
from django_admin_listfilter_dropdown.filters import (
    RelatedDropdownFilter, ChoiceDropdownFilter, DropdownFilter,
)

from .models import TerAdmin, SchoolType, School, SchoolCloster, QuestionCategory, Question


# Register your models here.
@admin.register(TerAdmin)
class TerAdminAdmin(admin.ModelAdmin):
    search_fields = ['name', ]
    list_display = ['name',]
    autocomplete_fields = ['representatives', ]


@admin.register(SchoolCloster)
class SchoolClosterAdmin(admin.ModelAdmin):
    pass


@admin.register(SchoolType)
class SchoolTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name')
    


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = [
        'ais_id',
        '__str__', 
        'id',
        'number',
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
    readonly_fields = ['ais_id', ]
    def get_readonly_fields(self, request, obj=None):
        if obj and request.user.groups.filter(name='Представитель ТУ/ДО').exists():
            return self.readonly_fields + [
                'name', 'short_name', 'email', 'city', 'number',
                'school_type', 'ter_admin', 'principal'
            ]
        return self.readonly_fields
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.groups.filter(name='Представитель ТУ/ДО').exists():
            return qs.filter(ter_admin__in=request.user.ter_admin.all())
        return qs

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