from django.contrib import messages
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .forms import EnquiryForm


def _safe_next(name):
    try:
        return reverse(name)
    except NoReverseMatch:
        return reverse("home")


@require_POST
@ratelimit(key="ip", rate="10/h", method="POST", block=True)
def submit_enquiry(request):
    form = EnquiryForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Thank you — we'll be in touch shortly.")
    else:
        # shortcut: redirect drops partially-typed values, inline errors when forms move to HTMX
        messages.error(request, f"Please check the form: {form.errors.as_text()}")
    return redirect(_safe_next(request.POST.get("next", "")))
