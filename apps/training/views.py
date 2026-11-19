import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.audit import log_action
from apps.accounts.decorators import staff_2fa_redirect, staff_required
from apps.accounts.models import User
from apps.accounts.pending import expiry, hash_token, make_token
from config.emails import (
    notify_certificate,
    notify_registration,
    notify_registration_status,
    notify_staff_new_registration,
    send_password_setup,
    send_pending_registration,
)

from .ai_advisor import analyze_career_trajectory
from .certificates import generate_certificate_pdf
from .forms import InboundEnrollmentForm, RegistrationForm
from .models import PendingRegistration, Programme, Registration


def _create_pending_registration(programme, email, message):
    token, token_hash = make_token()
    pending = PendingRegistration.objects.create(
        programme=programme,
        email=email,
        message=message,
        token_hash=token_hash,
        expires_at=expiry(),
    )
    send_pending_registration(pending, token)
    return pending


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


@ratelimit(key="ip", rate="40/h", method="POST", block=True)
def api_career_advisor(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else request.POST
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = request.POST

    current_role = data.get("current_role") or data.get("role") or ""
    experience = data.get("experience", "")
    interests = data.get("interests") or data.get("target_role") or ""

    result = analyze_career_trajectory(current_role, experience, interests)
    result["guidance"] = result.get("summary", "")
    return JsonResponse({"success": True, "data": result})


@require_POST
@ratelimit(key="ip", rate="30/h", method="POST", block=True)
def programme_register(request, slug):
    programme = get_object_or_404(Programme, slug=slug, published=True)
    if not programme.registration_open:
        messages.error(request, "Registration for this programme is closed.")
        return redirect("programme_detail", slug=programme.slug)

    if request.user.is_authenticated:
        if not request.user.is_student:
            messages.error(request, "Use a student account to register for training.")
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
                notify_staff_new_registration(registration)
            except IntegrityError:
                messages.error(request, "You are already registered for this programme.")
            return redirect("programme_detail", slug=programme.slug)
    else:
        # Inbound frictionless enrollment from LinkedIn/social
        form = InboundEnrollmentForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            full_name = form.cleaned_data["full_name"].strip()
            phone = form.cleaned_data.get("phone", "").strip()
            linkedin_url = form.cleaned_data.get("linkedin_url", "").strip()
            career_status = form.cleaned_data.get("career_status", "").strip()
            user_msg = form.cleaned_data.get("message", "").strip()
            generic_message = "If this email can be used, check your inbox to continue."

            parts = full_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

            combined_notes = []
            if career_status:
                combined_notes.append(f"[Career Status: {career_status}]")
            if linkedin_url:
                combined_notes.append(f"[LinkedIn: {linkedin_url}]")
            if user_msg:
                combined_notes.append(user_msg)
            message = "\n".join(combined_notes)

            existing_user = User.objects.filter(email__iexact=email).first()
            if existing_user:
                _create_pending_registration(programme, existing_user.email, message)
                messages.info(request, generic_message)
                return redirect("programme_detail", slug=programme.slug)

            try:
                student = User.objects.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    account_type=User.AccountType.STUDENT,
                    is_staff=False,
                )
                student.set_unusable_password()
                student.save()
            except IntegrityError:
                existing_user = User.objects.filter(email__iexact=email).first()
                if existing_user:
                    _create_pending_registration(
                        programme, existing_user.email, message
                    )
                messages.info(request, generic_message)
                return redirect("programme_detail", slug=programme.slug)

            registration, reg_created = Registration.objects.get_or_create(
                programme=programme,
                student=student,
                defaults={"message": message},
            )
            if reg_created:
                notify_registration(registration)
                notify_staff_new_registration(registration)
            send_password_setup(student)
            messages.info(request, generic_message)
            return redirect("programme_detail", slug=programme.slug)

    return redirect("programme_detail", slug=programme.slug)


@ratelimit(key="ip", rate="30/m", block=True)
def pending_registration(request, token):
    pending = get_object_or_404(
        PendingRegistration,
        token_hash=hash_token(token),
        consumed_at__isnull=True,
        expires_at__gt=timezone.now(),
    )
    user = User.objects.filter(email__iexact=pending.email, is_active=True).first()
    if not user:
        raise Http404
    if request.user.is_authenticated and request.user.pk != user.pk:
        raise Http404
    if not request.user.is_authenticated:
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    if not user.is_student:
        messages.error(request, "Use a student account to register for training.")
        return redirect("dashboard")

    if request.method == "POST":
        if Registration.objects.filter(
            programme=pending.programme, student=user
        ).exists():
            pending.consumed_at = timezone.now()
            pending.save(update_fields=["consumed_at"])
            messages.info(request, "You are already registered for this programme.")
            return redirect("dashboard")
        registration = Registration(
            programme=pending.programme,
            student=user,
            message=request.POST.get("message", pending.message)[:4000],
        )
        try:
            with transaction.atomic():
                registration.save()
                pending.consumed_at = timezone.now()
                pending.save(update_fields=["consumed_at"])
            notify_registration(registration)
            notify_staff_new_registration(registration)
            messages.success(request, "Your registration has been sent.")
            return redirect("dashboard")
        except IntegrityError:
            messages.info(request, "You are already registered for this programme.")
            return redirect("dashboard")

    return render(
        request,
        "training/pending_registration.html",
        {"pending": pending},
    )


def sap_scrum(request):
    programmes = visible_programmes().filter(
        category__name__in=["SAP", "Scrum & Agile"]
    ).select_related("category")
    return render(request, "pages/sap_scrum.html", {"programmes": programmes})


# shortcut: IP rate limit only; lengthen new certificate refs if enumeration becomes a concern.
@ratelimit(key="ip", rate="20/m", method="GET", block=True)
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
    if request.user.is_staff:
        blocked = staff_2fa_redirect(request)
        if blocked:
            return blocked
    registrations = Registration.objects.select_related("programme", "student")
    if request.user.is_admin:
        pass
    elif request.user.has_perm("training.view_registration"):
        registrations = registrations.filter(student__is_staff=False)
    else:
        if not request.user.is_student:
            raise Http404
        registrations = registrations.filter(student=request.user)
    registration = get_object_or_404(
        registrations, certificate_ref=ref, certificate_issued=True
    )
    response = HttpResponse(
        generate_certificate_pdf(registration), content_type="application/pdf"
    )
    filename = f"{ref}.pdf" if ref.startswith("GCTT-") else f"GCTT-{ref}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@staff_required
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
@staff_required
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
@staff_required
@permission_required("training.view_registration", raise_exception=True)
def staff_registrations(request):
    registrations = Registration.objects.select_related("programme", "student").filter(
        student__is_staff=False
    )
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
        registrations = (
            registrations.filter(programme_id=programme)
            if programme.isdigit()
            else registrations.none()
        )
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
@staff_required
@permission_required("training.change_registration", raise_exception=True)
@require_POST
def staff_registration_status(request, pk):
    registration = get_object_or_404(
        Registration.objects.filter(student__is_staff=False), pk=pk
    )
    status = request.POST.get("status", "")
    if status in STAFF_STATUSES:
        previous = registration.status
        if previous != status:
            registration.status = status
            registration.save(update_fields=["status"])
            log_action(
                request, "registration.status", f"{registration.pk}", f"{previous} → {status}"
            )
            notify_registration_status(registration)
            messages.success(request, "Status updated.")
    return redirect("staff_registrations")


@login_required
@staff_required
@permission_required("training.change_registration", raise_exception=True)
@require_POST
def staff_registration_certificate(request, pk):
    registration = get_object_or_404(
        Registration.objects.filter(student__is_staff=False), pk=pk
    )
    if request.POST.get("action") == "revoke":
        ref = registration.certificate_ref or ""
        registration.revoke_certificate()
        log_action(request, "certificate.revoke", ref)
        messages.success(request, "Certificate revoked.")
    elif registration.status == Registration.Status.COMPLETED:
        registration.issue_certificate()
        notify_certificate(registration, request)
        log_action(request, "certificate.issue", registration.certificate_ref, registration.programme.title)
        messages.success(request, f"Certificate issued: {registration.certificate_ref}")
    else:
        messages.error(request, "Set the registration to Completed before issuing a certificate.")
    return redirect("staff_registrations")
