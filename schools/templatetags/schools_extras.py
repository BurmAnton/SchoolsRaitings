from django import template
from django.db.models import Q
from schools.models import School, TerAdmin


register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def is_not_iro(user):
    from users.models import Group
    
    iro_group =  Group.objects.get(name='Представитель ИРО')
    return user.groups.filter(id=iro_group.id).count() != 1


@register.filter
def is_school_exist(user):
    school = School.objects.filter(principal=user, is_archived=False)
    return school.count() != 0


@register.filter
def is_ter_admin_exist(user):
    ter_admin = TerAdmin.objects.filter(representatives=user)
    return ter_admin.count() != 0


@register.filter
def filter_categories(categories, user) :
    categories_list = []
    for category in categories:
        if category.questions.filter(Q(is_visible=True) | Q(user=user)).count() > 0:
            categories_list.append(category)
    return categories_list
