from django import forms
from .models import Question, QuestionCategory

class ImportDataForm(forms.Form):
    import_file = forms.FileField(label="Импортируемый файл", max_length=100,
    widget=forms.ClearableFileInput)

    def __init__(self, *args, **kwargs):
        super(ImportDataForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question', 'category']