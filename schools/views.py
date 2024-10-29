from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .forms import ImportDataForm, QuestionForm
from . import imports
from .models import Question, QuestionCategory

# Create your views here.
@login_required
@csrf_exempt
def schools_import(request):
    form = ImportDataForm()
    response = None

    if request.method == 'POST':
        form = ImportDataForm(request.POST, request.FILES)
        if form.is_valid():
            response = imports.schools(form)
    
    return render(request, "schools/import_schools.html", {
        'form' : ImportDataForm(),
        'response': response,
    })


@login_required
@csrf_exempt
def questions(request):
    categories = QuestionCategory.objects.all()
    if request.user.is_superuser:
        questions = Question.objects.all()
    else:
        questions = Question.objects.filter(is_visible=True) | Question.objects.filter(user=request.user)

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            Question.objects.create(
                user=request.user,
                category= QuestionCategory.objects.get(id=request.POST['category']),
                short_question=request.POST['short_question'],
                question=form.cleaned_data['question'],
            )

    return render(request, "schools/questions.html", {
        'questions': questions,
        'categories': categories,
        'form': QuestionForm(),
    })