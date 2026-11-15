import io

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django_otp import login as otp_login
from django_ratelimit.decorators import ratelimit

from apps.enquiries.models import Enquiry
from apps.jobs.models import Application, Job
from apps.training.models import Programme, Registration
from config.emails import send_verification

from .forms import ProfileForm, SignupForm
from .models import User

INPUT = "w-full rounded-sm border border-line bg-white px-4 py-2.5"


@ratelimit(key="ip", rate="10/h", method="POST", block=True)
def signup(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        send_verification(user, request)
        messages.success(request, "Welcome to GCTT. Check your inbox to verify your email.")
        return redirect("dashboard")
    return render(request, "accounts/signup.html", {"form": form})


@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def login_view(request, *args, **kwargs):
    return LoginView.as_view(template_name="accounts/login.html")(request, *args, **kwargs)


def verify_email(request, uidb64, token):
    user = None
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        pass
    if user and default_token_generator.check_token(user, token):
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        messages.success(request, "Email verified — thank you.")
    else:
        messages.error(request, "That verification link is invalid or has expired.")
    return redirect("dashboard" if request.user.is_authenticated else "login")


@login_required
@require_POST
@ratelimit(key="user", rate="5/h", method="POST", block=True)
def resend_verification(request):
    if request.user.email_verified:
        messages.info(request, "Your email is already verified.")
    else:
        send_verification(request.user, request)
        messages.success(request, "Verification email sent.")
    return redirect("dashboard")


@login_required
def dashboard(request):
    if request.user.is_staff:
        return _staff_dashboard(request)
    return render(
        request,
        "accounts/dashboard.html",
        {
            "applications": request.user.applications.select_related("job"),
            "registrations": request.user.registrations.select_related("programme"),
        },
    )


def _staff_dashboard(request):
    user = request.user
    sections = []

    def add(label, url_name, perm, count, note=""):
        if user.has_perm(perm):
            sections.append({"label": label, "url": url_name, "count": count, "note": note})

    add("Enquiries", "staff_enquiries", "enquiries.view_enquiry",
        Enquiry.objects.filter(status=Enquiry.Status.NEW).count(), "new")
    add("Jobs", "staff_jobs", "jobs.view_job",
        Job.objects.count(), f"{Job.objects.filter(published=False).count()} awaiting review")
    add("Applications", "staff_applications", "jobs.view_application",
        Application.objects.count())
    add("Programmes", "staff_programmes", "training.view_programme",
        Programme.objects.count(), f"{Programme.objects.filter(published=False).count()} drafts")
    add("Registrations", "staff_registrations", "training.view_registration",
        Registration.objects.count())

    return render(
        request,
        "accounts/staff_dashboard.html",
        {
            "sections": sections,
            "is_ceo": user.is_superuser,
            "can_use_admin": user.is_superuser or user.has_perm("jobs.delete_job"),
        },
    )


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile saved.")
        return redirect("profile")
    return render(request, "accounts/profile_edit.html", {"form": form})


def _qr_svg(url):
    image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage)
    buffer = io.BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode()


@login_required
def security(request):
    user = request.user
    if not user.is_staff:
        raise PermissionDenied

    device = user.totpdevice_set.filter(confirmed=True).first()
    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "disable":
            if user.check_password(request.POST.get("password", "")):
                user.totpdevice_set.all().delete()
                messages.success(request, "Two-factor authentication disabled.")
            else:
                messages.error(request, "Password incorrect.")
            return redirect("security")
        target = device or user.totpdevice_set.filter(confirmed=False).last()
        if target and target.verify_token(request.POST.get("token", "").strip()):
            if not target.confirmed:
                target.confirmed = True
                target.save(update_fields=["confirmed"])
            otp_login(request, target)
            messages.success(request, "Two-factor authentication is active.")
        else:
            messages.error(request, "That code is not valid. Try again.")
        return redirect("security")

    qr_svg = secret = None
    if not device:
        pending = user.totpdevice_set.filter(confirmed=False).last()
        if pending is None:
            pending = user.totpdevice_set.create(name="default", confirmed=False)
        qr_svg = _qr_svg(pending.config_url)
        secret = pending.bin_key.hex().upper()
    return render(
        request,
        "accounts/security.html",
        {
            "device": device,
            "qr_svg": qr_svg,
            "secret": secret,
            "required": settings.REQUIRE_STAFF_2FA,
        },
    )
