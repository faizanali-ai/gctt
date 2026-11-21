from urllib.parse import urlparse

from django.conf import settings
from django.db import DatabaseError

from apps.accounts.models import SiteSettings
from apps.enquiries.forms import EnquiryForm

from .constants import COMPANY, DIVISIONS, NAV_ITEMS, SERVICES


def _is_active(path, prefixes):
    return any(path.startswith(prefix) for prefix in prefixes)


def _company():
    """Merge editable site settings over the constants, keeping every key.

    A database outage must not break error-page rendering, so fall back to the
    constants on any database error.
    """
    company = dict(COMPANY)
    try:
        record = SiteSettings.load()
    except DatabaseError:
        return company
    for key, value in (
        ("name", record.company_name),
        ("legal_name", record.legal_name),
        ("tagline", record.tagline),
        ("email", record.email),
        ("jobs_email", record.jobs_email),
        ("address", record.address),
        ("url", record.url.rstrip("/")),
    ):
        if value:
            company[key] = value
    company["jobsEmail"] = company["jobs_email"]
    company["domain"] = urlparse(company["url"]).netloc or COMPANY["domain"]
    company.update(
        {
            "hero_eyebrow": record.hero_eyebrow,
            "hero_title": record.hero_title,
            "hero_subtitle": record.hero_subtitle,
            "hero_cta_label": record.hero_cta_label,
            "hero_cta_url": record.hero_cta_url,
        }
    )
    return company


def site(request):
    path = request.path
    return {
        "COMPANY": _company(),
        "NAV_ITEMS": NAV_ITEMS,
        "NAV_DIVISIONS": [
            {**item, "active": _is_active(path, item["prefixes"])} for item in DIVISIONS
        ],
        "SERVICES": SERVICES,
        "EMAIL_OTP_ENABLED": settings.REQUIRE_EMAIL_OTP,
        # Repopulate a failed enquiry once, then clear it.
        "enquiry_form": EnquiryForm(initial=request.session.pop("enquiry_initial", {})),
    }
