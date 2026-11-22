import json

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import (
    MediaAsset,
    NavigationItem,
    PageContent,
    PageFAQ,
    SiteSettings,
    TeamProfile,
    User,
)


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
            "phone",
            "phone_raw",
            "address",
            "url",
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "hero_cta_label",
            "hero_cta_url",
            "announcement_banner_enabled",
            "announcement_banner_text",
            "announcement_banner_link",
            "allow_candidate_applications",
            "allow_student_registrations",
            "logo_light_url",
            "logo_dark_url",
        )
        widgets = {
            "hero_subtitle": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "company_name": "Company name",
            "legal_name": "Legal name",
            "tagline": "Brand tagline",
            "email": "Primary enquiry email",
            "jobs_email": "Careers / recruiting email",
            "phone": "Phone display (e.g. +1 (786) 855-8859)",
            "phone_raw": "Phone raw dial digits (e.g. +17868558859)",
            "address": "Office address",
            "url": "Canonical website URL",
            "hero_eyebrow": "Hero eyebrow",
            "hero_title": "Hero headline",
            "hero_subtitle": "Hero sub-text",
            "hero_cta_label": "Hero button text",
            "hero_cta_url": "Hero button link",
            "announcement_banner_enabled": "Enable global announcement banner at top of site",
            "announcement_banner_text": "Announcement banner message",
            "announcement_banner_link": "Announcement link URL (optional)",
            "allow_candidate_applications": "Accept candidate applications on Careers page",
            "allow_student_registrations": "Accept registrations on Training / Academy pages",
            "logo_light_url": "Light mode logo override URL (optional)",
            "logo_dark_url": "Dark mode logo override URL (optional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep non-core fields optional so existing automated test posts without them stay valid!
        optional_fields = (
            "phone",
            "phone_raw",
            "announcement_banner_enabled",
            "announcement_banner_text",
            "announcement_banner_link",
            "allow_candidate_applications",
            "allow_student_registrations",
            "logo_light_url",
            "logo_dark_url",
        )
        for f in optional_fields:
            if f in self.fields:
                self.fields[f].required = False

    def clean_hero_cta_url(self):
        value = (self.cleaned_data.get("hero_cta_url") or "").strip()
        if value and not value.startswith(("/", "http://", "https://")):
            raise ValidationError("Use a relative path or an http(s) URL.")
        return value

    def clean_announcement_banner_link(self):
        val = (self.cleaned_data.get("announcement_banner_link") or "").strip()
        if val and not val.startswith(("/", "http://", "https://")):
            raise ValidationError("Use a relative path or an http(s) URL.")
        return val


class PageContentForm(forms.ModelForm):
    sections_json = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 6, "class": "font-mono text-xs"}),
        required=False,
        label="Custom section data (JSON)",
        help_text="Optional key-value JSON for extra section headlines, body paragraphs, or bullet points.",
    )

    class Meta:
        model = PageContent
        fields = (
            "title",
            "meta_description",
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "hero_cta_label",
            "hero_cta_url",
        )
        widgets = {
            "meta_description": forms.Textarea(attrs={"rows": 2}),
            "hero_subtitle": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "title": "Page browser title / SEO title",
            "meta_description": "Meta description (search engines)",
            "hero_eyebrow": "Hero eyebrow tag",
            "hero_title": "Hero headline",
            "hero_subtitle": "Hero supporting paragraph",
            "hero_cta_label": "Hero primary button label",
            "hero_cta_url": "Hero primary button URL",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.required = False
        if self.instance and self.instance.pk and self.instance.sections_data:
            self.fields["sections_json"].initial = json.dumps(
                self.instance.sections_data, indent=2
            )

    def clean_sections_json(self):
        raw = (self.cleaned_data.get("sections_json") or "").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValidationError("Must be a valid JSON object (key-value pairs).")
            return parsed
        except json.JSONDecodeError as err:
            raise ValidationError(f"Invalid JSON format: {err}")

    def clean_hero_cta_url(self):
        val = (self.cleaned_data.get("hero_cta_url") or "").strip()
        if val and not val.startswith(("/", "http://", "https://", "mailto:", "tel:")):
            raise ValidationError("URL must be relative (/path/) or absolute (https://...)")
        return val

    def save(self, commit=True):
        instance = super().save(commit=False)
        if "sections_json" in self.cleaned_data:
            instance.sections_data = self.cleaned_data["sections_json"]
        if commit:
            instance.save()
        return instance


class PageFAQForm(forms.ModelForm):
    class Meta:
        model = PageFAQ
        fields = ("page_slug", "question", "answer", "order", "is_published")
        widgets = {
            "answer": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "page_slug": "Associated page",
            "question": "Question",
            "answer": "Answer text",
            "order": "Display order (lowest first)",
            "is_published": "Published (visible on page)",
        }


class NavigationItemForm(forms.ModelForm):
    class Meta:
        model = NavigationItem
        fields = ("menu", "label", "url", "order", "is_published", "open_in_new_tab")
        labels = {
            "menu": "Menu location",
            "label": "Link text",
            "url": "Destination URL (/page/ or https://...)",
            "order": "Sort order (lowest first)",
            "is_published": "Published (visible)",
            "open_in_new_tab": "Open in new browser tab",
        }

    def clean_url(self):
        val = (self.cleaned_data.get("url") or "").strip()
        if not val.startswith(("/", "http://", "https://", "mailto:", "tel:")):
            raise ValidationError("URL must be relative (/path/) or absolute (https://...)")
        return val


class MediaAssetForm(forms.ModelForm):
    class Meta:
        model = MediaAsset
        fields = ("title", "file", "alt_text")
        labels = {
            "title": "Asset title / name",
            "file": "Select image or document file",
            "alt_text": "Accessibility alt text (for images)",
        }


