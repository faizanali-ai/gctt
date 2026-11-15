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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", INPUT)
