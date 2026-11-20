from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "username" in self.fields:
            self.fields["username"].widget.attrs.setdefault("placeholder", "name@example.com")
            self.fields["username"].widget.attrs.setdefault("autocomplete", "email")
        if "password" in self.fields:
            self.fields["password"].widget.attrs.setdefault("placeholder", "••••••••")
            self.fields["password"].widget.attrs.setdefault("autocomplete", "current-password")


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("account_type", "email", "first_name", "last_name")
        widgets = {"account_type": forms.RadioSelect}
        labels = {"account_type": "I am a…"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.setdefault("autocomplete", "email")
        self.fields["email"].widget.attrs.setdefault("placeholder", "name@example.com")
        self.fields["first_name"].widget.attrs.setdefault("autocomplete", "given-name")
        self.fields["first_name"].widget.attrs.setdefault("placeholder", "First name")
        self.fields["last_name"].widget.attrs.setdefault("autocomplete", "family-name")
        self.fields["last_name"].widget.attrs.setdefault("placeholder", "Last name")
        self.fields["password1"].widget.attrs.setdefault("autocomplete", "new-password")
        self.fields["password2"].widget.attrs.setdefault("autocomplete", "new-password")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs.setdefault("autocomplete", "given-name")
        self.fields["last_name"].widget.attrs.setdefault("autocomplete", "family-name")
        self.fields["phone"].widget.attrs.setdefault("autocomplete", "tel")

