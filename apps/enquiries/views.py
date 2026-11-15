from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .forms import EnquiryForm
from .models import Enquiry


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


@login_required
@permission_required("enquiries.view_enquiry", raise_exception=True)
def staff_enquiries(request):
    return render(
        request,
        "staff/enquiries.html",
        {"enquiries": Enquiry.objects.all(), "statuses": Enquiry.Status.choices},
    )


@login_required
@permission_required("enquiries.change_enquiry", raise_exception=True)
@require_POST
def staff_enquiry_status(request, pk):
    enquiry = get_object_or_404(Enquiry, pk=pk)
    status = request.POST.get("status", "")
    if status in Enquiry.Status.values:
        enquiry.status = status
        enquiry.save(update_fields=["status"])
        messages.success(request, "Enquiry updated.")
    return redirect("staff_enquiries")
