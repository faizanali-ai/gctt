from django import forms

from .models import Category, Programme, Registration


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "published", "order")


class ProgrammeForm(forms.ModelForm):
    slug = forms.SlugField(
        required=False,
        help_text="Leave blank to generate from the title.",
    )

    class Meta:
        model = Programme
        fields = (
            "title",
            "slug",
            "category",
            "delivery_mode",
            "schedule",
            "duration",
            "description",
            "registration_open",
            "published",
            "order",
        )
        widgets = {"description": forms.Textarea(attrs={"rows": 6})}


class RegistrationManageForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ("status", "message")
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}


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
