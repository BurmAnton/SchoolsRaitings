from django.contrib import admin
from django.contrib.auth.models import Group as DefaultGroup
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django_admin_listfilter_dropdown.filters import (
    RelatedDropdownFilter, RelatedOnlyDropdownFilter, DropdownFilter,
)

from schools.models import School

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import User, Group, Permission, Documentation, MainPageArticle


# Register your models here.
admin.site.unregister(DefaultGroup)


@admin.register(MainPageArticle)
class MainPageArticleAdmin(admin.ModelAdmin):
    pass


@admin.register(Group)
class GroupAdmin(GroupAdmin):
    pass


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    pass

# @admin.register(Notification)
# class NotificationAdmin(admin.ModelAdmin):
#     pass

@admin.register(Documentation)
class DocumentationAdmin(admin.ModelAdmin):
    list_display = ('header', 'timestamp', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('header',)
    ordering = ('-timestamp',)

@admin.register(User)
class UserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm

    list_display = ('email', 'last_name', 'first_name', 'middle_name', 'ter_admin_list', 'groups_list')

    def ter_admin_list(self, obj):
        if obj.ter_admin.all().count() == 0:
            return "-"
        return ", ".join([ter_admin.name for ter_admin in obj.ter_admin.all()])
    ter_admin_list.short_description = "ТУ/ДО"

    def groups_list(self, obj):
        if obj.groups.count() == 0:
            return "-"
        return ", ".join([group.name for group in obj.groups.all()])
    groups_list.short_description = "Группа доступа"    

    search_fields = ('email','last_name', 'first_name', 'middle_name')
    list_filter = [
        ('groups', RelatedDropdownFilter),
        ('ter_admin', RelatedOnlyDropdownFilter)
    ]
    
    ordering = ('email',)

    fieldsets = (
        (None,
            {'fields': ('email', 'password', 'last_name', 'first_name', 'middle_name', 'phone_number')}),
        ('Права доступа',
            {   'classes': ['collapse'],
                'fields': ('is_superuser', 'is_staff', 'is_active', 'groups', 'user_permissions')}),
        ('Временные метки', 
            {
                'classes': ['collapse'],
                'fields': ('last_login', 'date_joined')
            }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.groups.filter(name='Представитель ТУ/ДО').exists():
            schools = School.objects.filter(ter_admin__in=request.user.ter_admin.all())
            return qs.filter(school__in=schools)
        return qs