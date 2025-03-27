from django.urls import path

from . import views

urlpatterns = [
    path('ter_admins/', views.ter_admins_reports, name='ter_admins_reports'),
    path('ter_admins/dash/', views.ter_admins_dash, name='ter_admins_dash'),
    path('ter_admins/school/', views.school_report, name='school_report'),
    path('ter_admins/closters/', views.closters_report, name='closters_report'),
    path('ter_admins/answers_distribution/', views.answers_distribution_report, name='answers_distribution_report'),
]