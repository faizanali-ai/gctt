import time

from django.conf import settings
from django.db import DatabaseError

from apps.enquiries.forms import EnquiryForm

from .constants import DIVISIONS, NAV_ITEMS, SERVICES
from .site import company

# Process-local dynamic navigation cache with a 30-second TTL.
# Cross-worker freshness contract:
# In multi-worker production deployments (e.g. 2 Gunicorn workers on Render),
# clearing this cache invalidates the handling worker immediately. Sibling workers
# will observe navigation updates on their next cache expiration (up to 30s delay).
# This bounded 30-second cross-worker delay is accepted architectural behavior to
# eliminate database roundtrips on public page loads without shared cache latency.
_NAV_CACHE: dict[str, object] = {"value": None, "expires_at": 0.0}


def clear_navigation_cache() -> None:
    _NAV_CACHE["value"] = None
    _NAV_CACHE["expires_at"] = 0.0


def _is_active(path, prefixes):
    return any(path.startswith(prefix) for prefix in prefixes)


def _get_dynamic_nav():
    now = time.monotonic()
    cached = _NAV_CACHE["value"]
    if cached is not None and now < float(_NAV_CACHE["expires_at"]):
        return cached

    try:
        from apps.accounts.models import NavigationItem

        items = list(NavigationItem.objects.filter(is_published=True).order_by("order", "id"))
        if not items:
            result = (None, None)
        else:
            header = [i for i in items if i.menu == "header"]
            footer = {
                "talent": [i for i in items if i.menu == "footer_talent"],
                "academy": [i for i in items if i.menu == "footer_academy"],
                "company": [i for i in items if i.menu == "footer_company"],
                "legal": [i for i in items if i.menu == "footer_legal"],
            }
            result = ((header or None), footer)

        _NAV_CACHE["value"] = result
        _NAV_CACHE["expires_at"] = now + 30.0
        return result
    except DatabaseError:
        return None, None


def site(request):
    path = request.path
    comp = company()
    dynamic_header, dynamic_footer = _get_dynamic_nav()
    return {
        "COMPANY": comp,
        "NAV_ITEMS": NAV_ITEMS,
        "NAV_DIVISIONS": [
            {**item, "active": _is_active(path, item["prefixes"])} for item in DIVISIONS
        ],
        "DYNAMIC_NAV_HEADER": dynamic_header,
        "DYNAMIC_NAV_FOOTER": dynamic_footer,
        "SERVICES": SERVICES,
        "EMAIL_OTP_ENABLED": settings.REQUIRE_EMAIL_OTP,
        "ANNOUNCEMENT_BANNER": {
            "enabled": comp.get("announcement_banner_enabled", False),
            "text": comp.get("announcement_banner_text", ""),
            "link": comp.get("announcement_banner_link", ""),
        },
        # Repopulate a failed enquiry once, then clear it.
        "enquiry_form": EnquiryForm(initial=request.session.pop("enquiry_initial", {})),
    }
