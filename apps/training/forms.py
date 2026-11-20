from django import forms

from .models import Registration


class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ("message",)
        widgets = {"message": forms.Textarea(attrs={"rows": 3})}
        labels = {"message": "Questions or target outcomes (optional)"}


class InboundEnrollmentForm(forms.Form):
    full_name = forms.CharField(
        label="Full name",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    phone = forms.CharField(
        label="Phone (optional)",
        max_length=40,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "tel"}),
    )
    linkedin_url = forms.URLField(
        label="LinkedIn (optional)",
        required=False,
        widget=forms.URLInput(attrs={"placeholder": "https://linkedin.com/in/username"}),
    )
    career_status = forms.CharField(
        label="Current status",
        max_length=100,
        required=False,
        widget=forms.Select(
            choices=[
                ("Seeking Next Role", "Actively looking"),
                ("Career Break", "Returning from a career break"),
                ("Employed / Upskilling", "Employed, upskilling"),
                ("College Graduate", "Recent graduate"),
            ]
        ),
    )
    message = forms.CharField(
        label="Background or goals (optional)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
