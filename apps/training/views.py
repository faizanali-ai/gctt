from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.audit import log_action
from config.emails import (
    notify_certificate,
    notify_registration,
    notify_registration_status,
)

from .certificates import generate_certificate_pdf
from .forms import RegistrationForm
from .models import Programme, Registration

STAFF_STATUSES = {
    Registration.Status.UNDER_REVIEW,
    Registration.Status.ACCEPTED,
    Registration.Status.REJECTED,
    Registration.Status.COMPLETED,
}


def visible_programmes():
    """Published programmes whose category (if any) is also published."""
    return Programme.objects.filter(published=True).filter(
        Q(category__isnull=True) | Q(category__published=True)
    )


def programme_list(request):
    programmes = visible_programmes().select_related("category")
    page_obj = Paginator(programmes, 12).get_page(request.GET.get("page"))
    return render(request, "training/programme_list.html", {"page_obj": page_obj})


def programme_detail(request, slug):
    programme = get_object_or_404(Programme, slug=slug)
    if not programme.published and not (
        request.user.is_staff and request.user.has_perm("training.view_programme")
    ):
        raise Http404
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
            notify_registration(registration)
        except IntegrityError:
            messages.error(request, "You are already registered for this programme.")
        return redirect("programme_detail", slug=programme.slug)
    return render(
        request,
        "training/programme_detail.html",
        {"programme": programme, "form": form, "registered": False},
    )


def sap_scrum(request):
    programmes = visible_programmes().filter(
        category__name__in=["SAP", "Scrum & Agile"]
    ).select_related("category")
    return render(request, "pages/sap_scrum.html", {"programmes": programmes})


def verify_certificate(request, ref=""):
    ref = ref or request.GET.get("ref", "").strip()
    registration = (
        Registration.objects.select_related("programme", "student")
        .filter(certificate_ref=ref, certificate_issued=True)
        .first()
    )
    return render(
        request, "training/verify.html", {"registration": registration, "ref": ref}
    )


@login_required
def download_certificate(request, ref):
    registration = get_object_or_404(
        Registration.objects.select_related("programme", "student"),
        certificate_ref=ref,
        certificate_issued=True,
    )
    if request.user != registration.student and not request.user.is_staff:
        return HttpResponseForbidden("This certificate belongs to another account.")
    response = HttpResponse(
        generate_certificate_pdf(registration), content_type="application/pdf"
    )
    response["Content-Disposition"] = f'attachment; filename="GCTT-{ref}.pdf"'
    return response


@login_required
@permission_required("training.view_programme", raise_exception=True)
def staff_programmes(request):
    programmes = Programme.objects.select_related("category")
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    published = request.GET.get("published", "")
    if q:
        programmes = programmes.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category:
        programmes = programmes.filter(category__name=category)
    if published in ("true", "false"):
        programmes = programmes.filter(published=published == "true")
    page_obj = Paginator(programmes, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "staff/programmes.html",
        {
            "page_obj": page_obj,
            "q": q,
            "category": category,
            "published": published,
            "categories": Programme.objects.exclude(category=None).values_list(
                "category__name", flat=True
            ).distinct(),
        },
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
        log_action(
            request,
            f"programme.{field}",
            programme.title,
            f"{field}={getattr(programme, field)}",
        )
        messages.success(request, f"{programme.title}: {field.replace('_', ' ')} updated.")
    return redirect("staff_programmes")


@login_required
@permission_required("training.view_registration", raise_exception=True)
def staff_registrations(request):
    registrations = Registration.objects.select_related("programme", "student")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    programme = request.GET.get("programme", "")
    if q:
        registrations = registrations.filter(
            Q(student__email__icontains=q)
            | Q(student__first_name__icontains=q)
            | Q(student__last_name__icontains=q)
            | Q(programme__title__icontains=q)
        )
    if status:
        registrations = registrations.filter(status=status)
    if programme:
        registrations = registrations.filter(programme_id=programme)
    page_obj = Paginator(registrations, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "staff/registrations.html",
        {
            "page_obj": page_obj,
            "q": q,
            "status": status,
            "programme": programme,
            "statuses": [
                choice for choice in Registration.Status.choices if choice[0] in STAFF_STATUSES
            ],
            "programmes": Programme.objects.all(),
            "all_statuses": Registration.Status.choices,
        },
    )


@login_required
@permission_required("training.change_registration", raise_exception=True)
@require_POST
def staff_registration_status(request, pk):
    registration = get_object_or_404(Registration, pk=pk)
    status = request.POST.get("status", "")
    if status in STAFF_STATUSES:
        previous = registration.status
        registration.status = status
        registration.save(update_fields=["status"])
        log_action(
            request, "registration.status", f"{registration.pk}", f"{previous} → {status}"
        )
        notify_registration_status(registration)
        messages.success(request, "Status updated.")
    return redirect("staff_registrations")


@login_required
@permission_required("training.change_registration", raise_exception=True)
@require_POST
def staff_registration_certificate(request, pk):
    registration = get_object_or_404(Registration, pk=pk)
    if request.POST.get("action") == "revoke":
        registration.revoke_certificate()
        log_action(request, "certificate.revoke", registration.certificate_ref or "")
        messages.success(request, "Certificate revoked.")
    elif registration.status == Registration.Status.COMPLETED:
        registration.issue_certificate()
        notify_certificate(registration, request)
        log_action(request, "certificate.issue", registration.certificate_ref, registration.programme.title)
        messages.success(request, f"Certificate issued: {registration.certificate_ref}")
    else:
        messages.error(request, "Set the registration to Completed before issuing a certificate.")
    return redirect("staff_registrations")
