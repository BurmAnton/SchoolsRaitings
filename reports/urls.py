from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('start/', views.start, name='start'),

    path('mo/reports/', views.mo_reports, name='mo_reports'),
    path('reports/<int:school_id>', views.reports, name='reports'),
    path('ter_admin/<int:user_id>/reports', views.ter_admin_reports, name='ter_admin_reports'),

    path('report/<int:s_report_id>/', views.mo_report, name='mo_report'),
    path('report/<int:report_id>/<int:school_id>', views.report, name='report'),
    path('ter_admin/<int:ter_admin_id>/report/<int:s_report_id>', views.ter_admin_report, name='ter_admin_report')
]