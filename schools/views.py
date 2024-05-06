from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .forms import ImportDataForm
from . import imports


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