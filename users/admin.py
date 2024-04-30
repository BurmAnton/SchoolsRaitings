from django.contrib import admin
from django.contrib.auth.models import Group as DefaultGroup
from django.contrib.auth.admin import GroupAdmin, UserAdmin

from .models import User, Group, Permission


# Register your models here.
admin.site.unregister(DefaultGroup)

@admin.register(Group)
class GroupAdmin(GroupAdmin):
    pass