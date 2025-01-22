# certificates/forms.py
from django import forms

class UploadEmailFileForm(forms.Form):
    file = forms.FileField()

class UploadCertificateForm(forms.Form):
    file = forms.FileField()

class SetCoordinatesForm(forms.Form):
    x = forms.FloatField()
    y = forms.FloatField()
