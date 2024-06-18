from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('reports/<int:school_id>', views.reports, name='reports'),
    path('report/<int:report_id>/<int:school_id>', views.report, name='report')
]