from django.conf import settings

from apps.enquiries.forms import EnquiryForm

from .constants import DIVISIONS, NAV_ITEMS, SERVICES
from .site import company


def _is_active(path, prefixes):
    return any(path.startswith(prefix) for prefix in prefixes)


def site(request):
    path = request.path
    return {
        "COMPANY": company(),
        "NAV_ITEMS": NAV_ITEMS,
        "NAV_DIVISIONS": [
            {**item, "active": _is_active(path, item["prefixes"])} for item in DIVISIONS
        ],
        "SERVICES": SERVICES,
        "EMAIL_OTP_ENABLED": settings.REQUIRE_EMAIL_OTP,
        # Repopulate a failed enquiry once, then clear it.
        "enquiry_form": EnquiryForm(initial=request.session.pop("enquiry_initial", {})),
    }
