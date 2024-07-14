from django import forms

class FileForm(forms.Form):
    form_file = forms.FileField(widget=forms.FileInput(attrs={'class':'form-control'}))