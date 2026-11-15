from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .forms import RegistrationForm
from .models import Programme, Registration

STAFF_STATUSES = {
    Registration.Status.UNDER_REVIEW,
    Registration.Status.ACCEPTED,
    Registration.Status.REJECTED,
    Registration.Status.COMPLETED,
}


def programme_list(request):
    programmes = Programme.objects.filter(published=True).select_related("category")
    return render(request, "training/programme_list.html", {"programmes": programmes})


def programme_detail(request, slug):
    programme = get_object_or_404(Programme, slug=slug, published=True)
    registered = (
        request.user.is_authenticated
        and programme.registrations.filter(student=request.user).exists()
    )
    return render(
        request,
        "training/programme_detail.html",
        {"programme": programme, "form": RegistrationForm(), "registered": registered},
    )


@require_POST
@login_required
@ratelimit(key="user", rate="20/h", method="POST", block=True)
def programme_register(request, slug):
    programme = get_object_or_404(Programme, slug=slug, published=True)
    if not programme.registration_open:
        messages.error(request, "Registration for this programme is closed.")
        return redirect("programme_detail", slug=programme.slug)
    form = RegistrationForm(request.POST)
    if form.is_valid():
        registration = form.save(commit=False)
        registration.programme = programme
        registration.student = request.user
        try:
            with transaction.atomic():
                registration.save()
            messages.success(request, "Your registration has been sent.")
        except IntegrityError:
            messages.error(request, "You are already registered for this programme.")
        return redirect("programme_detail", slug=programme.slug)
    return render(
        request,
        "training/programme_detail.html",
        {"programme": programme, "form": form, "registered": False},
    )


def sap_scrum(request):
    programmes = Programme.objects.filter(
        published=True, category__name__in=["SAP", "Scrum & Agile"]
    ).select_related("category")
    return render(request, "pages/sap_scrum.html", {"programmes": programmes})


@login_required
@permission_required("training.view_programme", raise_exception=True)
def staff_programmes(request):
    return render(
        request,
        "staff/programmes.html",
        {"programmes": Programme.objects.select_related("category")},
    )


@login_required
@permission_required("training.change_programme", raise_exception=True)
@require_POST
def staff_programme_toggle(request, pk):
    programme = get_object_or_404(Programme, pk=pk)
    field = request.POST.get("field")
    if field in ("published", "registration_open"):
        setattr(programme, field, not getattr(programme, field))
        programme.save(update_fields=[field])
        messages.success(request, f"{programme.title}: {field.replace('_', ' ')} updated.")
    return redirect("staff_programmes")


@login_required
@permission_required("training.view_registration", raise_exception=True)
def staff_registrations(request):
    return render(
        request,
        "staff/registrations.html",
        {
            "registrations": Registration.objects.select_related("programme", "student"),
            "statuses": [
                choice for choice in Registration.Status.choices if choice[0] in STAFF_STATUSES
            ],
        },
    )


@login_required
@permission_required("training.change_registration", raise_exception=True)
@require_POST
def staff_registration_status(request, pk):
    registration = get_object_or_404(Registration, pk=pk)
    status = request.POST.get("status", "")
    if status in STAFF_STATUSES:
        registration.status = status
        registration.save(update_fields=["status"])
        messages.success(request, "Status updated.")
    return redirect("staff_registrations")
