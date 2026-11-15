from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User

INPUT = "w-full rounded-sm border border-line bg-white px-4 py-2.5"


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("account_type", "email", "first_name", "last_name")
        widgets = {"account_type": forms.RadioSelect}
        labels = {"account_type": "I am a…"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "account_type":
                field.widget.attrs.setdefault("class", INPUT)
        self.fields["email"].widget.attrs.setdefault("autocomplete", "email")
        self.fields["first_name"].widget.attrs.setdefault("autocomplete", "given-name")
        self.fields["last_name"].widget.attrs.setdefault("autocomplete", "family-name")
        self.fields["password1"].widget.attrs.setdefault("autocomplete", "new-password")
        self.fields["password2"].widget.attrs.setdefault("autocomplete", "new-password")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. Use the log-in page instead."
            )
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", INPUT)
