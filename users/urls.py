from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('registration/', views.reg_view, name="reg_view"),
    path('registration/confirm/<int:user_id>/<str:token>', views.reg_confirm_view, name="reg_confirm_view"),
    
    path('documentation/', views.documentation, name='documentation'),

    path('undefined_user/', views.undefined_user, name='undefined_user'),

    # Password reset URLs
    path('password_reset/', views.password_reset_request, name='password_reset_request'),
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), 
         name='password_reset_complete'),
]