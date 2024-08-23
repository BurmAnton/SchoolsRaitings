from django.urls import path

from . import views

urlpatterns = [
    path('ter_admins/<int:report_id>', views.ter_admins_dash, name='ter_admins_dash'),
    path('ter_admins/reports', views.ter_admins_reports, name='ter_admins_reports'),
]