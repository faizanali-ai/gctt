import base64
import io

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django_otp import login as otp_login
from django_ratelimit.decorators import ratelimit

from apps.enquiries.models import Enquiry
from apps.jobs.models import Application, Job
from apps.training.models import Programme, Registration
from config.emails import send_verification

from .audit import log_action
from .forms import ProfileForm, SignupForm
from .models import User

INPUT = "w-full rounded-sm border border-line bg-white px-4 py-2.5"


@ratelimit(key="ip", rate="10/h", method="POST", block=True)
def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
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
    return LoginView.as_view(
        template_name="accounts/login.html", redirect_authenticated_user=True
    )(request, *args, **kwargs)


def verify_email(request, uidb64, token):
    user = None
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        pass
    if user and user.email_verified:
        messages.info(request, "Your email is already verified.")
    elif user and default_token_generator.check_token(user, token):
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
    stats = {}

    if user.has_perm("enquiries.view_enquiry"):
        stats["enquiries_new"] = Enquiry.objects.filter(status=Enquiry.Status.NEW).count()
        stats["enquiries_total"] = Enquiry.objects.count()

    if user.has_perm("jobs.view_job"):
        stats["jobs_active"] = Job.objects.filter(published=True).count()
        stats["jobs_drafts"] = Job.objects.filter(published=False).count()

    if user.has_perm("jobs.view_application"):
        stats["applications_total"] = Application.objects.count()
        stats["applications_submitted"] = Application.objects.filter(
            status=Application.Status.SUBMITTED
        ).count()

    if user.has_perm("training.view_programme"):
        stats["programmes_total"] = Programme.objects.count()
        stats["programmes_drafts"] = Programme.objects.filter(published=False).count()

    if user.has_perm("training.view_registration"):
        stats["registrations_total"] = Registration.objects.count()
        stats["registrations_pending"] = Registration.objects.filter(
            status=Registration.Status.SUBMITTED
        ).count()

    recent_applications = []
    if user.has_perm("jobs.view_application"):
        recent_applications = (
            Application.objects.select_related("job", "applicant")
            .order_by("-created_at")[:5]
        )

    recent_enquiries = []
    if user.has_perm("enquiries.view_enquiry"):
        recent_enquiries = Enquiry.objects.order_by("-created_at")[:5]

    recent_registrations = []
    if user.has_perm("training.view_registration"):
        recent_registrations = (
            Registration.objects.select_related("programme", "student")
            .order_by("-created_at")[:5]
        )

    return render(
        request,
        "accounts/staff_dashboard.html",
        {
            "stats": stats,
            "recent_applications": recent_applications,
            "recent_enquiries": recent_enquiries,
            "recent_registrations": recent_registrations,
            "can_manage_users": user.can_manage_users,
            "can_use_admin": user.is_owner,
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


def _require_user_manager(request):
    if not request.user.can_manage_users:
        raise PermissionDenied


@login_required
def manage_users(request):
    _require_user_manager(request)
    users = User.objects.filter(is_staff=True).exclude(role=User.Role.OWNER).select_related()
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    if q:
        users = users.filter(
            Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )
    if role:
        users = users.filter(role=role)
    page_obj = Paginator(users.order_by("role", "email"), 25).get_page(request.GET.get("page"))
    return render(
        request,
        "portals/users.html",
        {
            "page_obj": page_obj,
            "q": q,
            "role": role,
            "roles": [choice for choice in User.Role.choices if choice[0] != User.Role.OWNER],
        },
    )


@login_required
def manage_user_create(request):
    _require_user_manager(request)
    assignable = request.user.assignable_roles()
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        role = request.POST.get("role", "")
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        group_name = request.POST.get("group", "")
        password = request.POST.get("password", "")
        error = None
        if role not in [value for value, _ in assignable]:
            error = "You cannot assign that role."
        elif not email:
            error = "Email is required."
        elif User.objects.filter(email=email).exists():
            error = "A user with that email already exists."
        else:
            try:
                validate_password(password)
            except ValidationError as exc:
                error = " ".join(exc.messages)
        if error:
            messages.error(request, error)
        else:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_staff=True,
            )
            if role == User.Role.STAFF and group_name:
                user.groups.set(Group.objects.filter(name=group_name))
            elif role != User.Role.STAFF:
                # CEO and superadmins get full business permissions.
                user.groups.set(Group.objects.filter(name="Admin"))
            log_action(request, "user.create", user.email, f"role={user.role}")
            messages.success(
                request, f"{email} added as {user.get_role_display()}."
            )
            return redirect("manage_users")
    return render(
        request,
        "portals/user_form.html",
        {
            "mode": "create",
            "assignable": assignable,
            "groups": Group.objects.all(),
        },
    )


@login_required
def manage_user_edit(request, pk):
    _require_user_manager(request)
    target = get_object_or_404(User.objects.exclude(role=User.Role.OWNER), pk=pk)
    if not request.user.can_manage_account(target):
        raise PermissionDenied
    assignable = list(request.user.assignable_roles())
    if target.role not in [value for value, _ in assignable]:
        assignable.append((target.role, target.get_role_display()))
    if request.method == "POST":
        role = request.POST.get("role", target.role)
        if role not in [value for value, _ in assignable]:
            messages.error(request, "You cannot assign that role.")
        elif target == request.user and request.POST.get("is_active") != "on":
            messages.error(request, "You cannot deactivate your own account.")
        else:
            new_password = request.POST.get("password", "").strip()
            if new_password:
                try:
                    validate_password(new_password, user=target)
                except ValidationError as exc:
                    for problem in exc.messages:
                        messages.error(request, problem)
                    return render(
                        request,
                        "portals/user_form.html",
                        {
                            "mode": "edit",
                            "target": target,
                            "assignable": assignable,
                            "groups": Group.objects.all(),
                        },
                    )
            target.first_name = request.POST.get("first_name", "").strip()
            target.last_name = request.POST.get("last_name", "").strip()
            target.phone = request.POST.get("phone", "").strip()
            target.role = role
            target.is_active = request.POST.get("is_active") == "on"
            target.is_staff = True
            target.save()
            if role == User.Role.STAFF:
                target.groups.set(Group.objects.filter(name=request.POST.get("group", "")))
            else:
                target.groups.set(Group.objects.filter(name="Admin"))
            if new_password:
                target.set_password(new_password)
                target.save(update_fields=["password"])
            log_action(
                request, "user.edit", target.email, f"role={role}, active={target.is_active}"
            )
            messages.success(request, "User updated.")
            return redirect("manage_users")
    return render(
        request,
        "portals/user_form.html",
        {
            "mode": "edit",
            "target": target,
            "assignable": assignable,
            "groups": Group.objects.all(),
        },
    )


@login_required
@require_POST
def account_delete(request):
    if request.user.role == User.Role.OWNER:
        raise PermissionDenied
    if not request.user.check_password(request.POST.get("password", "")):
        messages.error(request, "Password incorrect. Your account was not deleted.")
        return redirect("profile")

    email = request.user.email
    log_action(request, "account.delete", email)
    request.user.delete()
    auth_logout(request)
    messages.success(request, "Your account and data have been permanently deleted.")
    return redirect("home")


def _qr_svg(url):
    image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage)
    buffer = io.BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode()


@login_required
def security(request):
    user = request.user

    device = user.totpdevice_set.filter(confirmed=True).first()
    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "disable":
            if user.check_password(request.POST.get("password", "")):
                user.totpdevice_set.all().delete()
                log_action(request, "security.2fa.disable", user.email)
                messages.success(request, "Two-factor authentication disabled.")
            else:
                messages.error(request, "Password incorrect.")
            return redirect("security")
        target = device or user.totpdevice_set.filter(confirmed=False).last()
        if target and target.verify_token(request.POST.get("token", "").strip()):
            if not target.confirmed:
                target.confirmed = True
                target.save(update_fields=["confirmed"])
                log_action(request, "security.2fa.enable", user.email)
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
        secret = base64.b32encode(pending.bin_key).decode("utf-8")
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
