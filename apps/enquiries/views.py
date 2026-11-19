from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.audit import log_action
from apps.accounts.decorators import staff_required
from config.emails import notify_enquiry, notify_enquiry_received

from .forms import EnquiryForm
from .models import Enquiry


def _safe_next(name):
    try:
        return reverse(name)
    except NoReverseMatch:
        return reverse("home")


CATEGORY_BY_PAGE = {
    "it_staffing": Enquiry.Category.IT_STAFFING,
    "recruitment": Enquiry.Category.RECRUITMENT,
    "talent_acquisition": Enquiry.Category.TALENT_ACQUISITION,
    "career_restart": Enquiry.Category.CAREER_RESTART,
    "employers": Enquiry.Category.EMPLOYER_INTAKE,
    "training": Enquiry.Category.TRAINING,
    "sap_scrum": Enquiry.Category.TRAINING,
}


@require_POST
@ratelimit(key="ip", rate="10/h", method="POST", block=True)
def submit_enquiry(request):
    form = EnquiryForm(request.POST)
    if form.is_valid():
        enquiry = form.save(commit=False)
        post_cat = request.POST.get("category", "").strip().lower()
        if post_cat in Enquiry.Category.values:
            enquiry.category = post_cat
        else:
            enquiry.category = CATEGORY_BY_PAGE.get(
                request.POST.get("next", ""), Enquiry.Category.GENERAL
            )
        enquiry.save()
        notify_enquiry(enquiry)
        notify_enquiry_received(enquiry)
        messages.success(request, "Thank you — we'll be in touch shortly.")
    else:
        # Keep what the visitor typed so a validation error never wipes their message.
        request.session["enquiry_initial"] = {
            key: value
            for key, value in request.POST.items()
            if key not in ("csrfmiddlewaretoken", "website", "next")
        }
        first_errors = [
            f"{field}: {errors[0]}" for field, errors in form.errors.items()
        ][:2]
        messages.error(request, "Please check: " + " · ".join(first_errors))
    return redirect(_safe_next(request.POST.get("next", "")))


@login_required
@staff_required
@permission_required("enquiries.view_enquiry", raise_exception=True)
def staff_enquiries(request):
    enquiries = Enquiry.objects.all()
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    category = request.GET.get("category", "")
    if q:
        enquiries = enquiries.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(message__icontains=q)
        )
    if status:
        enquiries = enquiries.filter(status=status)
    if category:
        enquiries = enquiries.filter(category=category)
    page_obj = Paginator(enquiries, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "staff/enquiries.html",
        {
            "page_obj": page_obj,
            "q": q,
            "status": status,
            "category": category,
            "statuses": Enquiry.Status.choices,
            "categories": Enquiry.Category.choices,
        },
    )


@login_required
@staff_required
@permission_required("enquiries.change_enquiry", raise_exception=True)
@require_POST
def staff_enquiry_status(request, pk):
    enquiry = get_object_or_404(Enquiry, pk=pk)
    status = request.POST.get("status", "")
    if status in Enquiry.Status.values:
        previous = enquiry.status
        if previous != status:
            enquiry.status = status
            enquiry.save(update_fields=["status"])
            log_action(request, "enquiry.status", f"{enquiry.pk}", f"{previous} → {status}")
            messages.success(request, "Enquiry updated.")
    return redirect("staff_enquiries")
