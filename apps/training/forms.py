from django import forms

from .models import Registration


class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ("message",)
        widgets = {"message": forms.Textarea(attrs={"rows": 3})}


class InboundEnrollmentForm(forms.Form):
    full_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=40, required=False)
    linkedin_url = forms.URLField(required=False)
    career_status = forms.CharField(max_length=100, required=False)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
