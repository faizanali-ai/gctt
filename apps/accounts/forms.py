import json
import re
from pathlib import Path

import defusedxml.ElementTree as ET
from defusedxml.common import DefusedXmlException
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

MEDIA_SIGNATURES = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "webp": (b"RIFF",),
    "pdf": (b"%PDF",),
    "docx": (b"PK\x03\x04",),
}
ALLOWED_MEDIA_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "svg", "pdf", "docx"}


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

    @staticmethod
    def _validate_safe_url(value, *, allow_contact_schemes=False):
        val = (value or "").strip()
        if val.startswith("//"):
            raise ValidationError(
                "Protocol-relative URLs starting with '//' are not allowed."
            )
        allowed = ("/", "https://", "mailto:", "tel:") if allow_contact_schemes else ("/", "https://")
        if val and not val.startswith(allowed):
            if allow_contact_schemes:
                raise ValidationError(
                    "URL must be a relative path (/path/) or secure absolute URL (https://...)."
                )
            raise ValidationError(
                "Logo URL must be a relative path (/path/) or secure absolute URL (https://...)."
            )
        return val

    def clean_hero_cta_url(self):
        return self._validate_safe_url(
            self.cleaned_data.get("hero_cta_url"), allow_contact_schemes=True
        )

    def clean_announcement_banner_link(self):
        return self._validate_safe_url(
            self.cleaned_data.get("announcement_banner_link"),
            allow_contact_schemes=True,
        )

    def clean_logo_light_url(self):
        return self._validate_safe_url(self.cleaned_data.get("logo_light_url"))

    def clean_logo_dark_url(self):
        return self._validate_safe_url(self.cleaned_data.get("logo_dark_url"))


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
            # Strict serialization check to reject non-finite numbers (NaN, Infinity) that Postgres cannot store
            json.dumps(parsed, allow_nan=False)
            return parsed
        except json.JSONDecodeError as err:
            raise ValidationError(f"Invalid JSON format: {err}")
        except (ValueError, TypeError) as err:
            raise ValidationError(f"Invalid JSON value: {err}")

    def clean_hero_cta_url(self):
        val = (self.cleaned_data.get("hero_cta_url") or "").strip()
        if val.startswith("//"):
            raise ValidationError("Protocol-relative URLs starting with '//' are not allowed.")
        if val and not val.startswith(("/", "https://", "mailto:", "tel:")):
            raise ValidationError("URL must be a relative path (/path/) or secure absolute URL (https://...).")
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
        if val.startswith("//"):
            raise ValidationError("Protocol-relative URLs starting with '//' are not allowed.")
        if not val.startswith(("/", "https://", "mailto:", "tel:")):
            raise ValidationError("URL must be a relative path (/path/) or secure absolute URL (https://...).")
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

    def clean_file(self):
        uploaded = self.cleaned_data.get("file")
        if not uploaded:
            raise ValidationError("Please choose a file to upload.")

        # 1. 10 MB maximum file limit to protect storage quotas
        if uploaded.size > 10 * 1024 * 1024:
            raise ValidationError("File size exceeds the 10 MB limit.")

        ext = Path(uploaded.name).suffix.lower().lstrip(".")
        if ext not in ALLOWED_MEDIA_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file type (.{ext}). Allowed: {', '.join(sorted(ALLOWED_MEDIA_EXTENSIONS))}."
            )

        # 2. Inspect magic bytes for binary formats
        head = uploaded.read(16)
        uploaded.seek(0)

        if ext == "svg":
            content = uploaded.read().decode("utf-8", errors="ignore")
            uploaded.seek(0)
            content_lower = content.lower()
            if (
                re.search(r"<\s*script", content_lower)
                or re.search(r"\bon\w+\s*=", content_lower)
                or re.search(r"(?:href|xlink:href)\s*=\s*['\"]?\s*javascript:", content_lower)
            ):
                raise ValidationError("SVG contains unsafe script elements or event handlers.")
            try:
                root = ET.fromstring(content)
                for elem in root.iter():
                    tag = elem.tag.lower()
                    if tag.endswith(("script", "foreignobject", "iframe", "object", "embed")):
                        raise ValidationError("SVG contains unsafe script elements or event handlers.")
                    for attr, val in elem.attrib.items():
                        attr_lower = attr.lower()
                        if attr_lower.startswith("on") or ":on" in attr_lower:
                            raise ValidationError("SVG contains unsafe script elements or event handlers.")
                        cleaned_val = re.sub(r"[\s\x00-\x1f\x7f-\x9f]", "", val.lower())
                        if "javascript:" in cleaned_val or "data:text/html" in cleaned_val:
                            raise ValidationError("SVG contains unsafe script elements or event handlers.")
            except DefusedXmlException:
                raise ValidationError("SVG contains unsafe XML entities or structure.")
            except ValidationError:
                raise
            except (ET.ParseError, ValueError, TypeError):
                raise ValidationError("Invalid or unparseable SVG file.")
        elif ext in MEDIA_SIGNATURES:
            signatures = MEDIA_SIGNATURES[ext]
            if not any(head.startswith(sig) for sig in signatures):
                raise ValidationError(f"File content does not match the .{ext} extension.")

        return uploaded


