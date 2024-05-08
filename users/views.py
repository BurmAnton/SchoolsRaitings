import random
import string
from urllib.parse import urljoin

from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from schools.models import School
from .tokens import account_activation_token
from .models import User, Group

# Create your views here.
@csrf_exempt
def login_view(request):
    error_message = None
    redirect = request.GET.get('next', '')
    
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]
        redirect = request.POST["next"]
        
        user = authenticate(request, email=email, password=password)
        if user is not None: 
            login(request, user)
        else:
            error_message = "Неверный логин/пароль!"

    if request.user.is_authenticated:
        if redirect == '':
                redirect = reverse("index")
        return HttpResponseRedirect(redirect)

    return render(request, "users/login.html", {
        "error_message": error_message,
        "next": redirect
    })


@login_required
@csrf_exempt
def logout_view(request):
    redirect = request.GET.get('next', '')
    logout(request)
    
    if redirect == '': 
        redirect = reverse("login_view")
    return HttpResponseRedirect(redirect)


def send_confirm_link(confirm_link, user, token):
    send_mail(
        "Подтверждения регистрации в АИС «Рейтингование ОО»",
        f"Ссылка для подтверждения регистрации в АИС «Рейтингование ОО»: {confirm_link}.",
        "a.burmatsky@gmail.com",
        [user.email,],
        fail_silently=False,
    )


@csrf_exempt
def reg_view(request):
    message = None

    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]
        conf_password = request.POST["conf_password"]
        if School.objects.filter(email=email).count() == 0:
            message = {
                "message_type": "danger", 
                "message":"Школа с такой электронной почтой не найдена! Нужно использовать официальную почту школы (@samara.edu.ru)."
            }
        elif password != conf_password:
            message = {"message_type": "danger",  "message":"Пароли не совпадают!"}
        elif User.objects.filter(email=email) != 0:
            message = {"message_type": "danger",  "message":"Аккаунт школы с таким email уже зарегистрирован!"}
        else:
            middle_name = request.POST["middle_name"]
            if middle_name == "": middle_name = None
            
            user = User.objects.create(
                email=email,
                is_active=False,
                first_name=request.POST["first_name"],
                last_name=request.POST["last_name"],
                middle_name=middle_name,
                phone_number=request.POST["phone_number"]
            )
            user.set_password(password)
            user.save()
            group, _ = Group.objects.get_or_create(name="Представитель школы")
            user.groups.add(group)
            school = School.objects.get(email=email)
            school.principal = user
            school.save()

            token = account_activation_token.make_token(user)
            confirm_link = request.build_absolute_uri(reverse('reg_confirm_view', args=[user.pk, token]))
            send_confirm_link(confirm_link, user, token)
            message = {
                "message_type": "success", 
                "message":"Регистрация прошла успешно, для завершения регистрации мы выслали Вам письмо со ссылкой на страницу подтверждения регистрации."
            }

    return render(request, "users/reg.html", {
        "message": message
    })


def reg_confirm_view(request, user_id, token):
    is_confirmed = False
    user = None
    try:
        user = User.objects.get(pk=user_id)
    except: pass
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        is_confirmed = True
    
    return render(request, "users/reg_confirm.html", {
        "is_confirmed": is_confirmed,
        user: user
    })
        
        