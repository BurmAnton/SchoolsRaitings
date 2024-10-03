from django.urls import path

from . import views

urlpatterns = [
    path('reports', views.ter_admins_reports, name='ter_admins_reports'),
    path('ter_admins/', views.ter_admins_dash, name='ter_admins_dash'),
    path('school/years', views.school_report, name='school_report'),
    path('closters/years', views.closters_report, name='closters_report'),
]