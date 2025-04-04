from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = User
        fields = ('email',)
        


class CustomUserChangeForm(UserChangeForm):
    

    class Meta:
        model = User
        fields = ('email',)


class PasswordResetForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=254, required=True)

