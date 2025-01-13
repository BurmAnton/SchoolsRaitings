from django.contrib import admin
from django.urls import reverse
from django_admin_listfilter_dropdown.filters import (
    RelatedDropdownFilter, ChoiceDropdownFilter, DropdownFilter,
)
from django.utils.safestring import mark_safe

from users.models import User

from .models import TerAdmin, SchoolType, School, SchoolCloster, QuestionCategory, Question


# Register your models here.
@admin.register(TerAdmin)
class TerAdminAdmin(admin.ModelAdmin):
    search_fields = ['name', ]

    list_display = ['name', 'representatives_list']
    
    def representatives_list(self, obj):
        if obj.representatives.count() == 0:
            return "-"
        return ", ".join([repr.email for repr in obj.representatives.all()])
    representatives_list.short_description = "Представители"

    autocomplete_fields = ['representatives', ]


@admin.register(SchoolCloster)
class SchoolClosterAdmin(admin.ModelAdmin):
    pass


@admin.register(SchoolType)
class SchoolTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name')
    


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_per_page = 50
    actions = ['export_schools']

    def export_schools(self, request, queryset):
        import openpyxl
        from django.http import HttpResponse
        from openpyxl.styles import Font, Alignment

        workbook = openpyxl.Workbook()
        worksheet = workbook.active

        headers = [
            "ID в АИС \"Кадры в образовании\"",
            "Полное наименование",
            "Сокращенное наименование",
            "Уровень образования",
            "Кластер",
            "Номер школы",
            "Тип школы",
            "Email",
            "ТУ/ДО",
            "Населённый пункт",
        ]

        # Write headers
        for col, header in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
            worksheet.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20

        # Write data
        ed_levels = {
            'A': "1 — 11 классы",
            'M': "1 — 9 классы",
            'S': "1 — 4 классы",
            'G': "10 — 11 классы",
            'MG': "5 — 11 классы",
            None: "",
            'True': "",
        }
        for row, school in enumerate(queryset, 2):
            
            data = [
                school.ais_id,
                school.name,
                school.short_name,
                ed_levels[school.ed_level],
                school.closter,
                school.number,
                school.school_type,
                school.email,
                school.ter_admin,
                school.city,
            ]
            for col, value in enumerate(data, 1):
                cell = worksheet.cell(row=row, column=col)
                if value is not None and value != "'True":
                    cell.value = str(value)
                cell.alignment = Alignment(horizontal='center')

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="schools.xlsx"'
        workbook.save(response)
        return response
    export_schools.short_description = "Экспортировать выбранные школы"
    
    list_display = [
        'ais_id',
        '__str__', 
        'number',
        'reports_page_link',
        'ter_admin',
        'closter_field',
        'ed_level', 
        'email',
        'principal',
    ]
    fields = [
        'ais_id',
        'name',
        'short_name',
        'email',
        'city',
        'number',
        
        'school_type',
        'closter',
        'ed_level',
        'ter_admin', 
        'principal',
        'principal_phone',
        # 'principal_email',
    ]

    def reports_page_link(self, obj):
        return mark_safe(f'<a href="{reverse("reports", kwargs={"school_id": obj.id})}">Личный кабинет</a>')
    reports_page_link.short_description = "Личный кабинет"

    def principal_phone(self, obj):
        if obj.principal.phone_number is None:
            return "-"
        return obj.principal.phone_number
    principal_phone.short_description = "Телефон директора"

    def principal_email(self, obj):
        if obj.principal.email is None:
            return "-"
        return obj.principal.email
    principal_email.short_description = "Email директора"

    def closter_field(self, obj):
        return obj.closter
    closter_field.admin_order_field = 'closter'
    closter_field.short_description = 'Кластер'

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
    readonly_fields = ['ais_id', 'principal_phone', 'principal_email']
    def get_readonly_fields(self, request, obj=None):
        if obj and request.user.groups.filter(name='Представитель ТУ/ДО').exists():
            return self.readonly_fields + [
                'name', 'short_name', 'email', 'city', 'number',
                'school_type', 'ter_admin', 'principal', 
            ]
        return self.readonly_fields
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.groups.filter(name='Представитель ТУ/ДО').exists():
            return qs.filter(ter_admin__in=request.user.ter_admin.all())
        return qs

    def save_model(self, request, obj, form, change):
        if obj.principal and obj.email:
            obj.principal.email = obj.email
            obj.principal.save()
        super().save_model(request, obj, form, change)

@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    pass

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['category', 'is_resolved', 'short_question', 'created_at']
    list_filter = [
        ('category', RelatedDropdownFilter), 
        'is_resolved',
        'is_visible',
    ]