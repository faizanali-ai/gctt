from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User

INPUT = "w-full rounded-sm border border-line bg-white px-4 py-2.5"


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("account_type", "company_name", "email", "first_name", "last_name")
        widgets = {"account_type": forms.RadioSelect}
        labels = {"account_type": "I am a…", "company_name": "Company name"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ("account_type", "company_name"):
                field.widget.attrs.setdefault("class", INPUT)
        self.fields["company_name"].widget.attrs.setdefault("class", INPUT)
        self.fields["company_name"].help_text = "Only needed for employer accounts."

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("account_type") == User.AccountType.EMPLOYER and not cleaned.get(
            "company_name", ""
        ).strip():
            self.add_error("company_name", "Employers must enter their company name.")
        return cleaned


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "company_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", INPUT)
