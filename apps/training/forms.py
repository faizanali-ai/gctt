from django import forms

from .models import Registration


class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ("message",)
        widgets = {"message": forms.Textarea(attrs={"rows": 3})}
