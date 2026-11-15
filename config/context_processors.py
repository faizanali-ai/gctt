from apps.enquiries.forms import EnquiryForm

from .constants import COMPANY, NAV_ITEMS, SERVICES


def site(request):
    return {
        "COMPANY": COMPANY,
        "NAV_ITEMS": NAV_ITEMS,
        "SERVICES": SERVICES,
        # Repopulate a failed enquiry once, then clear it.
        "enquiry_form": EnquiryForm(initial=request.session.pop("enquiry_initial", {})),
    }
