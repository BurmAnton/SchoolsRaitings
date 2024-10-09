from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('registration/', views.reg_view, name="reg_view"),
    path('registration/confirm/<int:user_id>/<str:token>', views.reg_confirm_view, name="reg_confirm_view"),
    
    path('documentation/', views.documentation, name='documentation'),

    path('undefined_user/', views.undefined_user, name='undefined_user'),
]