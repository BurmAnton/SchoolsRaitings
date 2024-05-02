from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

# Create your views here.
@csrf_exempt
def login_view(request):
    error_message = None
    redirect = request.GET.get('next', '')
    
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]
        next = request.POST["next"]
        user = authenticate(request, email=email, password=password)
        if user is not None: 
            login(request, user)
        else:
            error_message = "Неверный логин/пароль!"

    if request.user.is_authenticated:
        if redirect == '':
                redirect = reverse("admin:index")
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
    
    if redirect_url == '': 
        redirect_url = reverse("login")
    return HttpResponseRedirect(redirect)
