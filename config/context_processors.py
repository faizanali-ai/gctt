from apps.enquiries.forms import EnquiryForm

from .constants import COMPANY, NAV_ITEMS, SERVICES


def site(request):
    return {
        "COMPANY": COMPANY,
        "NAV_ITEMS": NAV_ITEMS,
        "SERVICES": SERVICES,
        "enquiry_form": EnquiryForm(),
    }
