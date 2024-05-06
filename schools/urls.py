from django.urls import path

from . import views

urlpatterns = [
    path('import/', views.schools_import, name='schools_import'),
]