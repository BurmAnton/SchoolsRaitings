from django.urls import path

from . import views

urlpatterns = [
    path('ter_admins/', views.ter_admins_reports, name='ter_admins_reports'),
    path('ter_admins/dash/', views.ter_admins_dash, name='ter_admins_dash'),
    path('ter_admins/school/', views.school_report, name='school_report'),
    path('ter_admins/closters/', views.closters_report, name='closters_report'),
    path('ter_admins/closters/debug/', views.debug_closters_report, name='debug_closters_report'),
    path('ter_admins/closters/debug-auth/', views.debug_auth_status, name='debug_auth_status'),
    path('ter_admins/answers_distribution/', views.answers_distribution_report, name='answers_distribution_report'),
    path('ajax/schools-by-ter-admin/', views.get_schools_by_ter_admin, name='get_schools_by_ter_admin'),
]