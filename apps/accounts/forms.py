from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import SiteSettings, TeamProfile, User


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
    promotional_opt_in = forms.BooleanField(
        required=False,
        label="Send me occasional offers and programme news",
        help_text="We will email you once to confirm. You can unsubscribe at any time.",
    )

    class Meta:
        model = User
        fields = (
            "account_type",
            "email",
            "first_name",
            "last_name",
        )
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


class TeamProfileForm(forms.ModelForm):
    class Meta:
        model = TeamProfile
        fields = (
            "section",
            "name",
            "designation",
            "bio",
            "linkedin_url",
            "photo_url",
            "order",
            "published",
        )
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}


class ProfileForm(forms.ModelForm):
    promotional_opt_in = forms.BooleanField(
        required=False,
        label="Send me occasional offers and programme news",
        help_text="We will email you once to confirm. You can unsubscribe at any time.",
    )

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "phone",
            "job_title",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs.setdefault("autocomplete", "given-name")
        self.fields["last_name"].widget.attrs.setdefault("autocomplete", "family-name")
        self.fields["phone"].widget.attrs.setdefault("autocomplete", "tel")
        self.fields["job_title"].widget.attrs.setdefault(
            "autocomplete", "organization-title"
        )
        self.fields["job_title"].widget.attrs.setdefault(
            "placeholder", "e.g. SAP Functional Consultant"
        )
        self.fields["promotional_opt_in"].initial = bool(
            self.instance.promotional_opt_in
            or self.instance.promotional_opt_in_requested_at
        )


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = (
            "company_name",
            "legal_name",
            "tagline",
            "email",
            "jobs_email",
            "address",
            "url",
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "hero_cta_label",
            "hero_cta_url",
        )
        widgets = {"hero_subtitle": forms.Textarea(attrs={"rows": 3})}
        labels = {
            "company_name": "Company name",
            "legal_name": "Legal name",
            "hero_eyebrow": "Hero eyebrow",
            "hero_title": "Hero headline",
            "hero_subtitle": "Hero sub-text",
            "hero_cta_label": "Hero button text",
            "hero_cta_url": "Hero button link",
        }

