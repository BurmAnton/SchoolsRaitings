from django.contrib import admin

from .models import TerAdmin, SchoolType, School


# Register your models here.
@admin.register(TerAdmin)
class TerAdminAdmin(admin.ModelAdmin):
    pass


@admin.register(SchoolType)
class SchoolTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name')


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'ter_admin', 'principal', 'email')
    