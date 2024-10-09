from django import template

from schools.models import School, TerAdmin


register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def is_school_exist(user):
    school = School.objects.filter(principal=user)
    return school.count() != 0


@register.filter
def is_ter_admin_exist(user):
    ter_admin = TerAdmin.objects.filter(representative=user)
    return ter_admin.count() != 0
