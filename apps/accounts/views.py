import json
import logging
import secrets
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.views import (
    LoginView,
    PasswordChangeView,
    PasswordResetConfirmView,
)
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.tokens import email_verification_token_generator
from apps.enquiries.models import Enquiry
from apps.jobs.models import Application, Job
from apps.training.models import Programme, Registration
from config.context_processors import clear_navigation_cache
from config.emails import (
    PROMOTIONAL_OPT_IN_MAX_AGE,
    send_account_deleted,
    send_email_changed,
    send_login_otp,
    send_password_changed,
    send_password_setup,
    send_promotional_opt_in,
    send_verification,
    send_welcome_if_first_login,
)

from .audit import log_action
from .decorators import staff_required
from .email_otp import clear_issue_cooldown, issue_code, verify_code
from .forms import (
    MediaAssetForm,
    NavigationItemForm,
    PageContentForm,
    PageFAQForm,
    ProfileForm,
    SignupForm,
    SiteSettingsForm,
    StyledAuthenticationForm,
    TeamProfileForm,
)
from .models import (
    DESIGNATION_CHOICES,
    MENU_CHOICES,
    PAGE_CHOICES,
    STAFF_SUBGROUPS,
    AuditLog,
    MediaAsset,
    NavigationItem,
    PageContent,
    PageFAQ,
    SiteSettings,
    TeamProfile,
    User,
)

logger = logging.getLogger(__name__)


def _notify_safely(label, callback):
    try:
        callback()
    except Exception:
        logger.exception("Account notification failed: %s", label)


@ratelimit(key="ip", rate="10/h", method="POST", block=True)
def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        existing = User.objects.filter(email__iexact=email).first()
        if existing:
            send_password_setup(existing)
            messages.success(
                request, "If this email can be used, check your inbox to continue."
            )
            return redirect("login")
        if form.is_valid():
            requested_promotions = form.cleaned_data.get("promotional_opt_in", False)
            try:
                user = form.save()
            except IntegrityError:
                messages.info(
                    request, "If this email can be used, check your inbox to continue."
                )
                return redirect("login")
            if requested_promotions:
                user.promotional_opt_in = False
                user.promotional_opt_in_requested_at = timezone.now()
                user.save(
                    update_fields=[
                        "promotional_opt_in",
                        "promotional_opt_in_requested_at",
                    ]
                )
                send_promotional_opt_in(user)
            send_verification(user, request)
            messages.success(
                request, "If this email can be used, check your inbox to continue."
            )
            return redirect("login")
    return render(request, "accounts/signup.html", {"form": form})


def _mask_email(email):
    if "@" in email:
        local, domain = email.split("@", 1)
        if len(local) > 2:
            return f"{local[:2]}***@{domain}"
        return f"{local[:1]}***@{domain}"
    return email


class CustomLoginView(LoginView):
    form_class = StyledAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        if user.requires_email_otp and settings.REQUIRE_EMAIL_OTP:
            return _start_email_otp(
                self.request, user, self.get_success_url()
            )
        response = super().form_valid(form)
        send_welcome_if_first_login(user)
        return response


class PasswordChangeNotifyView(PasswordChangeView):
    def form_valid(self, form):
        response = super().form_valid(form)
        _notify_safely(
            "password change", lambda: send_password_changed(self.request.user)
        )
        return response


class PasswordResetConfirmNotifyView(PasswordResetConfirmView):
    def form_valid(self, form):
        response = super().form_valid(form)
        _notify_safely(
            "password reset", lambda: send_password_changed(self.user)
        )
        return response


@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def login_view(request, *args, **kwargs):
    return CustomLoginView.as_view()(request, *args, **kwargs)


def _safe_next(request, value):
    if value and url_has_allowed_host_and_scheme(
        value, allowed_hosts={request.get_host()}
    ):
        return value
    return None


def _start_email_otp(request, user, next_url=None):
    """Send a code to a known/authenticated user without asking for email again."""
    email = user.email.strip().lower()
    request.session["email_otp_email"] = email
    next_url = _safe_next(request, next_url)
    if next_url:
        request.session["email_otp_next"] = next_url
    else:
        request.session.pop("email_otp_next", None)

    issued = issue_code(email)
    if issued:
        if send_login_otp(email, issued[1]):
            log_action(request, "auth.email_otp_request", email)
        else:
            issued[0].delete()
            clear_issue_cooldown(email)
            log_action(request, "auth.email_otp_send_failed", _mask_email(email))
            messages.error(
                request,
                "We could not send a sign-in code just now. Please try again.",
            )
            return redirect("email_otp_verify")

    messages.info(
        request,
        "If this email can be used, check your inbox for a sign-in code.",
    )
    return redirect("email_otp_verify")


def _complete_email_otp_login(request, user):
    next_url = request.session.pop("email_otp_next", None)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    send_welcome_if_first_login(user)
    if next_url:
        return redirect(next_url)
    return redirect("dashboard")


@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def email_otp_request(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if not settings.REQUIRE_EMAIL_OTP:
        messages.info(request, "Email code sign-in is currently disabled.")
        return redirect("login")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        next_url = _safe_next(request, request.POST.get("next", ""))

        user = (
            User.objects.filter(email__iexact=email, is_active=True)
            .filter(Q(is_staff=True) | Q(role=User.Role.ADMIN))
            .first()
        )
        if user:
            return _start_email_otp(request, user, next_url)

        request.session["email_otp_email"] = email
        if next_url:
            request.session["email_otp_next"] = next_url
        else:
            request.session.pop("email_otp_next", None)

        log_action(
            request, "auth.email_otp_request_unknown", _mask_email(email)
        )

        messages.info(
            request,
            "If this email can be used, check your inbox for a sign-in code.",
        )
        return redirect("email_otp_verify")

    return render(
        request,
        "accounts/login_email_otp.html",
        {"next": _safe_next(request, request.GET.get("next", "")) or ""},
    )


@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def email_otp_verify(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if not settings.REQUIRE_EMAIL_OTP:
        return redirect("login")

    email = request.session.get("email_otp_email", "")
    if not email:
        return redirect("email_otp_request")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        if verify_code(email, code):
            user = (
                User.objects.filter(email__iexact=email, is_active=True)
                .filter(Q(is_staff=True) | Q(role=User.Role.ADMIN))
                .first()
            )
            if user:
                if not user.email_verified:
                    user.email_verified = True
                    user.save(update_fields=["email_verified"])
                request.session.pop("email_otp_email", None)
                log_action(request, "auth.email_otp", user.email)
                return _complete_email_otp_login(request, user)
            messages.error(request, "That code is invalid or expired.")
        else:
            log_action(request, "auth.email_otp_failed", _mask_email(email))
            messages.error(request, "That code is invalid or expired.")

    return render(
        request,
        "accounts/login_email_otp_verify.html",
        {"masked_email": _mask_email(email)},
    )


@require_POST
@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def email_otp_resend(request):
    if not settings.REQUIRE_EMAIL_OTP:
        return redirect("login")

    email = request.session.get("email_otp_email", "")
    if not email:
        return redirect("email_otp_request")

    user = (
        User.objects.filter(email__iexact=email, is_active=True)
        .filter(Q(is_staff=True) | Q(role=User.Role.ADMIN))
        .first()
    )
    if user:
        issued = issue_code(email)
        if issued:
            if send_login_otp(email, issued[1]):
                log_action(request, "auth.email_otp_resend", email)
            else:
                issued[0].delete()
                clear_issue_cooldown(email)
                log_action(
                    request, "auth.email_otp_send_failed", _mask_email(email)
                )
                messages.error(
                    request,
                    "We could not send a sign-in code just now. Please try again.",
                )
                return redirect("email_otp_verify")

    messages.info(
        request,
        "If this email can be used, check your inbox for a sign-in code.",
    )
    return redirect("email_otp_verify")


def legacy_2fa_redirect(request):
    return redirect("login")


@ratelimit(key="ip", rate="20/m", method="GET", block=True)
def google_login(request):
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        messages.warning(
            request,
            "Google Sign-In is being initialized on this domain. Please use your email and password below.",
        )
        return redirect("login")

    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state

    next_url = request.GET.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        request.session["google_oauth_next"] = next_url
    else:
        request.session.pop("google_oauth_next", None)

    account_type = request.GET.get("account_type", "")
    if account_type in (User.AccountType.CANDIDATE, User.AccountType.STUDENT):
        request.session["google_oauth_account_type"] = account_type

    redirect_uri = request.build_absolute_uri(reverse("google_callback"))
    if not settings.DEBUG and redirect_uri.startswith("http://"):
        redirect_uri = "https://" + redirect_uri[len("http://") :]

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return redirect(
        f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    )


@ratelimit(key="ip", rate="20/m", method="GET", block=True)
def google_callback(request):
    error = request.GET.get("error")
    if error:
        messages.error(
            request, f"Google authentication was cancelled or encountered an error ({error})."
        )
        return redirect("login")

    code = request.GET.get("code")
    state = request.GET.get("state")
    saved_state = request.session.pop("google_oauth_state", None)

    if not code or not state or not saved_state or state != saved_state:
        messages.error(request, "Invalid or expired Google authentication session. Please try again.")
        return redirect("login")

    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "").strip()
    client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        messages.error(request, "Google Sign-In configuration is missing server credentials.")
        return redirect("login")

    redirect_uri = request.build_absolute_uri(reverse("google_callback"))
    if not settings.DEBUG and redirect_uri.startswith("http://"):
        redirect_uri = "https://" + redirect_uri[len("http://") :]

    token_payload = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    token_req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(token_req, timeout=10) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        messages.error(
            request, "Unable to communicate with Google authentication servers. Please try again."
        )
        return redirect("login")

    access_token = token_data.get("access_token")
    if not access_token:
        messages.error(request, "Failed to retrieve access credentials from Google.")
        return redirect("login")

    userinfo_req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(userinfo_req, timeout=10) as resp:
            user_info = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        messages.error(request, "Unable to verify profile details with Google.")
        return redirect("login")

    email = (user_info.get("email") or "").strip().lower()
    email_verified = user_info.get("email_verified", False)

    if not email or not email_verified:
        messages.error(request, "Google account does not have a verified email address.")
        return redirect("login")

    user = User.objects.filter(email__iexact=email).first()
    if user:
        if not user.is_active:
            messages.error(request, "Unable to sign in with this Google account. Please contact support.")
            return redirect("login")
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])

        if user.requires_email_otp and settings.REQUIRE_EMAIL_OTP:
            return _start_email_otp(
                request, user, request.session.pop("google_oauth_next", None)
            )

        log_action(request, "auth.google_login", user.email)
    else:
        account_type = request.session.pop(
            "google_oauth_account_type", User.AccountType.CANDIDATE
        )
        if account_type not in (User.AccountType.CANDIDATE, User.AccountType.STUDENT):
            account_type = User.AccountType.CANDIDATE

        first_name = (user_info.get("given_name") or "")[:150]
        last_name = (user_info.get("family_name") or "")[:150]
        if not first_name and user_info.get("name"):
            names = user_info["name"].split(None, 1)
            first_name = names[0][:150]
            if len(names) > 1:
                last_name = names[1][:150]

        try:
            user = User.objects.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                account_type=account_type,
            )
        except IntegrityError:
            messages.error(request, "Unable to complete sign-in. Please try again.")
            return redirect("login")
        user.is_staff = False
        user.is_superuser = False
        user.email_verified = True
        user.set_unusable_password()
        user.save()
        log_action(request, "auth.google_signup", user.email)
        messages.success(request, f"Welcome to GCTT, {user.first_name or user.email}!")

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    send_welcome_if_first_login(user)

    next_url = request.session.pop("google_oauth_next", None)
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("dashboard")


def verify_email(request, uidb64, token):
    user = None
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        pass
    if user and user.email_verified:
        messages.info(request, "Your email is already verified.")
    elif user and email_verification_token_generator.check_token(user, token):
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
    context = {}
    if request.user.is_candidate:
        context["applications"] = request.user.applications.select_related("job")
    elif request.user.is_student:
        context["registrations"] = request.user.registrations.select_related("programme")
    return render(request, "accounts/dashboard.html", context)


def _staff_dashboard(request):
    user = request.user
    stats = {}

    if user.is_admin:
        stats = {
            "accounts_total": User.objects.count(),
            "admins_total": User.objects.filter(role=User.Role.ADMIN, is_active=True).count(),
            "staff_total": User.objects.filter(role=User.Role.STAFF, is_staff=True).count(),
            "candidates_total": User.objects.filter(
                account_type=User.AccountType.CANDIDATE, is_staff=False
            ).count(),
            "students_total": User.objects.filter(
                account_type=User.AccountType.STUDENT, is_staff=False
            ).count(),
            "enquiries_new": Enquiry.objects.filter(status=Enquiry.Status.NEW).count(),
            "enquiries_total": Enquiry.objects.count(),
            "jobs_active": Job.objects.filter(published=True).count(),
            "jobs_drafts": Job.objects.filter(published=False).count(),
            "applications_total": Application.objects.count(),
            "applications_submitted": Application.objects.filter(
                status=Application.Status.SUBMITTED
            ).count(),
            "programmes_total": Programme.objects.count(),
            "programmes_drafts": Programme.objects.filter(published=False).count(),
            "registrations_total": Registration.objects.count(),
            "registrations_pending": Registration.objects.filter(
                status=Registration.Status.SUBMITTED
            ).count(),
        }

    recent_applications = []
    if user.has_perm("jobs.view_application"):
        recent_applications = (
            Application.objects.select_related("job", "applicant")
            .filter(applicant__is_staff=False)
            .order_by("-created_at")[:5]
        )

    recent_enquiries = []
    if user.has_perm("enquiries.view_enquiry"):
        recent_enquiries = Enquiry.objects.order_by("-created_at")[:5]

    recent_registrations = []
    if user.has_perm("training.view_registration"):
        recent_registrations = (
            Registration.objects.select_related("programme", "student")
            .filter(student__is_staff=False)
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
            "can_use_admin": user.is_admin,
        },
    )


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        requested_promotions = form.cleaned_data.get("promotional_opt_in", False)
        form.save()
        if requested_promotions and not request.user.promotional_opt_in:
            request.user.promotional_opt_in = False
            request.user.promotional_opt_in_requested_at = timezone.now()
            request.user.save(
                update_fields=[
                    "promotional_opt_in",
                    "promotional_opt_in_requested_at",
                ]
            )
            if send_promotional_opt_in(request.user):
                messages.info(
                    request,
                    "Check your email and confirm to start receiving offers.",
                )
            else:
                messages.info(
                    request,
                    "A confirmation email was requested recently. Please check your inbox.",
                )
        elif not requested_promotions and (
            request.user.promotional_opt_in
            or request.user.promotional_opt_in_requested_at
        ):
            request.user.promotional_opt_in = False
            request.user.promotional_opt_in_requested_at = None
            request.user.save(
                update_fields=[
                    "promotional_opt_in",
                    "promotional_opt_in_requested_at",
                ]
            )
        messages.success(request, "Profile saved.")
        return redirect("profile")
    return render(request, "accounts/profile_edit.html", {"form": form})


def _require_user_manager(request):
    if not request.user.can_manage_users:
        raise PermissionDenied


def _active_admin_count():
    return User.objects.filter(
        role=User.Role.ADMIN, is_active=True, is_staff=True
    ).count()


@login_required
@staff_required
def manage_users(request):
    _require_user_manager(request)
    users = User.objects.prefetch_related("groups")
    q = request.GET.get("q", "").strip()
    designation = request.GET.get("designation", request.GET.get("role", ""))
    if q:
        users = users.filter(
            Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )
    if designation == "admin":
        users = users.filter(role=User.Role.ADMIN)
    elif designation == "staff":
        users = users.filter(role=User.Role.STAFF, is_staff=True)
    elif designation == "candidate":
        users = users.filter(
            is_staff=False, account_type=User.AccountType.CANDIDATE
        )
    elif designation == "student":
        users = users.filter(is_staff=False, account_type=User.AccountType.STUDENT)
    page_obj = Paginator(users.order_by("role", "email"), 25).get_page(request.GET.get("page"))
    return render(
        request,
        "portals/users.html",
        {
            "page_obj": page_obj,
            "q": q,
            "designation": designation,
            "designations": DESIGNATION_CHOICES,
        },
    )


def _validate_admin_user_fields(email, first_name, last_name, phone, job_title):
    errors = []
    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors.append("Enter a valid email address.")
        if len(email) > User._meta.get_field("email").max_length:
            errors.append("Email address is too long.")
    for label, value, max_length in (
        ("First name", first_name, User._meta.get_field("first_name").max_length),
        ("Last name", last_name, User._meta.get_field("last_name").max_length),
        ("Phone", phone, User._meta.get_field("phone").max_length),
        ("Job title", job_title, User._meta.get_field("job_title").max_length),
    ):
        if len(value) > max_length:
            errors.append(f"{label} must be {max_length} characters or fewer.")
    return errors


def _submitted_designation(request, fallback="staff"):
    value = (
        request.POST.get("designation")
        or request.POST.get("role")
        or fallback
    )
    return value if value in {choice[0] for choice in DESIGNATION_CHOICES} else fallback


@login_required
@staff_required
def manage_user_create(request):
    _require_user_manager(request)
    subgroups = Group.objects.filter(name__in=STAFF_SUBGROUPS)
    selected_designation = _submitted_designation(request)
    selected_group = request.POST.get("group", "")
    form_errors = []
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        job_title = request.POST.get("job_title", "").strip()
        subgroup = request.POST.get("group", "")
        password = request.POST.get("password", "")
        is_active = request.POST.get("is_active", "on") == "on"
        email_verified = request.POST.get("email_verified", "on") == "on"
        error = None
        field_errors = _validate_admin_user_fields(
            email, first_name, last_name, phone, job_title
        )
        if not email:
            error = "Email is required."
        elif field_errors:
            error = " ".join(field_errors)
        elif selected_designation == "staff" and subgroup not in STAFF_SUBGROUPS:
            error = "Select a valid staff subgroup."
        elif User.objects.filter(email__iexact=email).exists():
            error = "A user with that email already exists."
        else:
            try:
                validate_password(password)
            except ValidationError as exc:
                error = " ".join(exc.messages)
        if error:
            messages.error(request, error)
            form_errors = [error]
        else:
            try:
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    job_title=job_title,
                    is_active=is_active,
                    email_verified=email_verified,
                )
                user.apply_designation(selected_designation, subgroup)
            except IntegrityError:
                messages.error(request, "A user with that email already exists.")
                form_errors = ["A user with that email already exists."]
            else:
                log_action(
                    request,
                    "user.create",
                    user.email,
                    f"designation={selected_designation}",
                )
                messages.success(request, f"{email} added as {user.designation}.")
                return redirect("manage_users")
    return render(
        request,
        "portals/user_form.html",
        {
            "mode": "create",
            "groups": subgroups,
            "designations": DESIGNATION_CHOICES,
            "selected_designation": selected_designation,
            "selected_group": selected_group,
            "values": request.POST,
            "form_errors": form_errors,
            "is_active_value": request.POST.get("is_active", "on") == "on",
            "email_verified_value": request.POST.get("email_verified", "on") == "on",
        },
    )


@login_required
@staff_required
def manage_user_edit(request, pk):
    _require_user_manager(request)
    target = get_object_or_404(User, pk=pk)
    if not request.user.can_manage_account(target):
        raise PermissionDenied
    old_email = target.email
    subgroups = Group.objects.filter(name__in=STAFF_SUBGROUPS)
    current_subgroup = target.groups.filter(name__in=STAFF_SUBGROUPS).values_list(
        "name", flat=True
    ).first()
    selected_designation = _submitted_designation(request, target.designation_value)
    selected_group = request.POST.get("group", current_subgroup or "")
    form_errors = []
    if request.method == "POST":
        email = request.POST.get("email", target.email).strip().lower()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        job_title = request.POST.get("job_title", target.job_title).strip()
        subgroup = request.POST.get("group", current_subgroup or "")
        is_active = request.POST.get("is_active") == "on"
        email_verified = (
            request.POST.get("email_verified") == "on"
            if "email_verified" in request.POST
            else target.email_verified
        )
        email_changed = email != old_email.lower()
        field_errors = _validate_admin_user_fields(
            email, first_name, last_name, phone, job_title
        )
        error = None
        if not email:
            error = "Email is required."
        elif field_errors:
            error = " ".join(field_errors)
        elif User.objects.filter(email__iexact=email).exclude(pk=target.pk).exists():
            error = "A user with that email already exists."
        elif selected_designation == "staff" and subgroup not in STAFF_SUBGROUPS:
            error = "Select a valid staff subgroup."
        elif target == request.user and selected_designation != "admin":
            error = "You cannot change your own admin designation."
        elif target == request.user and not is_active:
            error = "You cannot deactivate your own account."
        elif (
            target.is_admin
            and (selected_designation != "admin" or not is_active)
            and _active_admin_count() <= 1
        ):
            error = "You cannot remove the last active admin."
        if error:
            messages.error(request, error)
            form_errors = [error]
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
                            "groups": subgroups,
                            "designations": DESIGNATION_CHOICES,
                            "selected_designation": selected_designation,
                            "selected_group": selected_group,
                            "values": request.POST,
                            "form_errors": exc.messages,
                            "is_active_value": is_active,
                            "email_verified_value": email_verified,
                        },
                    )
            target.email = email
            target.first_name = first_name
            target.last_name = last_name
            target.phone = phone
            target.job_title = job_title
            target.is_active = is_active
            target.email_verified = False if email_changed else email_verified
            target.apply_designation(selected_designation, subgroup)
            if new_password:
                target.set_password(new_password)
                target.save(update_fields=["password"])
            if email_changed:
                _notify_safely(
                    "email change",
                    lambda: send_email_changed(target, old_email),
                )
                _notify_safely(
                    "new email verification",
                    lambda: send_verification(target, request),
                )
            if new_password:
                _notify_safely(
                    "admin password change",
                    lambda: send_password_changed(target),
                )
            log_action(
                request,
                "user.edit",
                target.email,
                f"designation={selected_designation}, active={target.is_active}",
            )
            messages.success(request, "User updated.")
            return redirect("manage_users")
    return render(
        request,
        "portals/user_form.html",
        {
            "mode": "edit",
            "target": target,
            "groups": subgroups,
            "designations": DESIGNATION_CHOICES,
            "selected_designation": selected_designation,
            "selected_group": selected_group,
            "values": request.POST,
            "form_errors": form_errors,
            "is_active_value": (
                request.POST.get("is_active") == "on"
                if request.method == "POST"
                else target.is_active
            ),
            "email_verified_value": (
                request.POST.get("email_verified") == "on"
                if request.method == "POST" and "email_verified" in request.POST
                else target.email_verified
            ),
        },
    )


@login_required
@staff_required
@require_POST
def manage_user_delete(request, pk):
    _require_user_manager(request)
    target = get_object_or_404(User, pk=pk)
    if not request.user.can_manage_account(target):
        raise PermissionDenied
    if target == request.user:
        messages.error(request, "You cannot delete your own account from user management.")
        return redirect("manage_users")
    if target.is_admin and _active_admin_count() <= 1:
        messages.error(request, "You cannot delete the last active admin.")
        return redirect("manage_users")

    target_email = target.email
    target.delete()
    log_action(request, "manage.user_delete", target_email)
    messages.success(request, f"User account {target_email} has been permanently deleted.")
    return redirect("manage_users")


@login_required
@staff_required
def manage_team(request):
    _require_user_manager(request)
    profiles = TeamProfile.objects.all()
    q = request.GET.get("q", "").strip()
    section = request.GET.get("section", "")
    if q:
        profiles = profiles.filter(
            Q(name__icontains=q)
            | Q(designation__icontains=q)
            | Q(bio__icontains=q)
        )
    if section in TeamProfile.Section.values:
        profiles = profiles.filter(section=section)
    page_obj = Paginator(profiles, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "staff/team.html",
        {
            "page_obj": page_obj,
            "q": q,
            "section": section,
            "sections": TeamProfile.Section.choices,
        },
    )


@login_required
@staff_required
def manage_team_create(request):
    _require_user_manager(request)
    form = TeamProfileForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        profile = form.save()
        log_action(request, "team.create", profile.name, profile.designation)
        messages.success(request, f"{profile.name} added.")
        return redirect("manage_team")
    return render(
        request,
        "staff/team_form.html",
        {"form": form, "mode": "create"},
    )


@login_required
@staff_required
def manage_team_edit(request, pk):
    _require_user_manager(request)
    profile = get_object_or_404(TeamProfile, pk=pk)
    form = TeamProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "team.edit", profile.name, profile.designation)
        messages.success(request, "Team profile updated.")
        return redirect("manage_team")
    return render(
        request,
        "staff/team_form.html",
        {"form": form, "mode": "edit", "profile": profile},
    )


@login_required
@staff_required
@require_POST
def manage_team_delete(request, pk):
    _require_user_manager(request)
    profile = get_object_or_404(TeamProfile, pk=pk)
    name = profile.name
    profile.delete()
    log_action(request, "team.delete", name)
    messages.success(request, f"{name} removed.")
    return redirect("manage_team")


@login_required
@staff_required
@ratelimit(key="user_or_ip", rate="60/m", block=True)
def manage_site_settings(request):
    _require_user_manager(request)
    form = SiteSettingsForm(request.POST or None, instance=SiteSettings.load())
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "settings.update", "site")
        messages.success(request, "Site settings saved.")
        return redirect("manage_site_settings")
    return render(
        request,
        "portals/site_settings.html",
        {"form": form},
    )


@login_required
@staff_required
def manage_audit(request):
    _require_user_manager(request)
    entries = AuditLog.objects.select_related("actor")
    q = request.GET.get("q", "").strip()
    action = request.GET.get("action", "").strip()
    if q:
        entries = entries.filter(
            Q(actor__email__icontains=q)
            | Q(action__icontains=q)
            | Q(target__icontains=q)
            | Q(details__icontains=q)
        )
    if action:
        entries = entries.filter(action=action)
    page_obj = Paginator(entries, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "staff/audit.html",
        {
            "page_obj": page_obj,
            "q": q,
            "action": action,
            "actions": (
                AuditLog.objects.order_by("action")
                .values_list("action", flat=True)
                .distinct()
            ),
        },
    )


@login_required
@staff_required
def manage_pages(request):
    _require_user_manager(request)
    contents = {pc.page_slug: pc for pc in PageContent.objects.select_related("updated_by")}
    faq_counts = {}
    for item in PageFAQ.objects.values("page_slug").annotate(total=Count("id")):
        faq_counts[item["page_slug"]] = item["total"]

    pages_list = []
    for slug, label in PAGE_CHOICES:
        pc = contents.get(slug)
        pages_list.append(
            {
                "slug": slug,
                "label": label,
                "has_content": bool(pc),
                "updated_at": pc.updated_at if pc else None,
                "updated_by": pc.updated_by if pc else None,
                "hero_title": pc.hero_title if pc else "",
                "faq_count": faq_counts.get(slug, 0),
            }
        )
    return render(request, "portals/pages.html", {"pages_list": pages_list})


@login_required
@staff_required
@ratelimit(key="user_or_ip", rate="60/m", block=True)
def manage_page_edit(request, page_slug):
    _require_user_manager(request)
    slug_dict = dict(PAGE_CHOICES)
    if page_slug not in slug_dict:
        messages.error(request, f"Unknown page slug: {page_slug}")
        return redirect("manage_pages")

    page_label = slug_dict[page_slug]
    instance, _ = PageContent.objects.get_or_create(page_slug=page_slug)
    form = PageContentForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        pc = form.save(commit=False)
        pc.updated_by = request.user
        pc.save()
        log_action(request, "page.edit", page_slug, pc.hero_title)
        messages.success(request, f"Content for '{page_label}' saved successfully.")
        return redirect("manage_page_edit", page_slug=page_slug)

    faqs = PageFAQ.objects.filter(page_slug=page_slug).order_by("order", "id")
    faq_form = PageFAQForm(initial={"page_slug": page_slug, "order": faqs.count() + 1})

    return render(
        request,
        "portals/page_edit.html",
        {
            "page_slug": page_slug,
            "page_label": page_label,
            "form": form,
            "faqs": faqs,
            "faq_form": faq_form,
        },
    )


@login_required
@staff_required
@require_POST
@ratelimit(key="user_or_ip", rate="60/m", block=True)
def manage_faq_create(request, page_slug):
    _require_user_manager(request)
    form = PageFAQForm(request.POST)
    if form.is_valid():
        faq = form.save()
        log_action(request, "faq.create", faq.page_slug, faq.question)
        messages.success(request, "FAQ added successfully.")
    else:
        messages.error(request, "Could not add FAQ. Please check all fields.")
    return redirect("manage_page_edit", page_slug=page_slug)


@login_required
@staff_required
def manage_faq_edit(request, pk):
    _require_user_manager(request)
    faq = get_object_or_404(PageFAQ, pk=pk)
    form = PageFAQForm(request.POST or None, instance=faq)
    if request.method == "POST" and form.is_valid():
        faq = form.save()
        log_action(request, "faq.edit", faq.page_slug, faq.question)
        messages.success(request, "FAQ updated successfully.")
        return redirect("manage_page_edit", page_slug=faq.page_slug)
    return render(
        request,
        "portals/faq_edit.html",
        {
            "faq": faq,
            "form": form,
        },
    )


@login_required
@staff_required
@require_POST
def manage_faq_delete(request, pk):
    _require_user_manager(request)
    faq = get_object_or_404(PageFAQ, pk=pk)
    page_slug = faq.page_slug
    question = faq.question
    faq.delete()
    log_action(request, "faq.delete", page_slug, question)
    messages.success(request, f"FAQ '{question}' deleted.")
    return redirect("manage_page_edit", page_slug=page_slug)


@login_required
@staff_required
@ratelimit(key="user_or_ip", rate="60/m", block=True)
def manage_navigation(request):
    _require_user_manager(request)
    items = NavigationItem.objects.all().order_by("menu", "order", "id")
    form = NavigationItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        nav_item = form.save()
        clear_navigation_cache()
        log_action(request, "nav.create", nav_item.menu, f"{nav_item.label} -> {nav_item.url}")
        messages.success(request, f"Navigation link '{nav_item.label}' added.")
        return redirect("manage_navigation")

    menus_dict = {key: [] for key, _ in MENU_CHOICES}
    for item in items:
        menus_dict.setdefault(item.menu, []).append(item)

    menus = []
    for key, label in MENU_CHOICES:
        menus.append(
            {
                "key": key,
                "label": label,
                "items": menus_dict.get(key, []),
            }
        )

    return render(
        request,
        "portals/navigation.html",
        {
            "menus": menus,
            "form": form,
            "menu_choices": MENU_CHOICES,
        },
    )


@login_required
@staff_required
def manage_navigation_edit(request, pk):
    _require_user_manager(request)
    item = get_object_or_404(NavigationItem, pk=pk)
    form = NavigationItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        clear_navigation_cache()
        log_action(request, "nav.edit", item.menu, f"{item.label} -> {item.url}")
        messages.success(request, f"Navigation link '{item.label}' updated.")
        return redirect("manage_navigation")
    return render(
        request,
        "portals/navigation_edit.html",
        {
            "item": item,
            "form": form,
        },
    )


@login_required
@staff_required
@require_POST
def manage_navigation_delete(request, pk):
    _require_user_manager(request)
    item = get_object_or_404(NavigationItem, pk=pk)
    label = item.label
    menu = item.menu
    item.delete()
    clear_navigation_cache()
    log_action(request, "nav.delete", menu, label)
    messages.success(request, f"Navigation link '{label}' removed.")
    return redirect("manage_navigation")


@login_required
@staff_required
@ratelimit(key="user_or_ip", rate="60/m", block=True)
def manage_media(request):
    _require_user_manager(request)
    form = MediaAssetForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        asset = form.save(commit=False)
        asset.uploaded_by = request.user
        asset.save()
        log_action(request, "media.upload", asset.title, asset.file.url)
        messages.success(request, f"Asset '{asset.title}' uploaded successfully.")
        return redirect("manage_media")

    assets = MediaAsset.objects.all().order_by("-uploaded_at")
    q = request.GET.get("q", "").strip()
    if q:
        assets = assets.filter(Q(title__icontains=q) | Q(alt_text__icontains=q))
    page_obj = Paginator(assets, 24).get_page(request.GET.get("page"))

    return render(
        request,
        "portals/media.html",
        {
            "page_obj": page_obj,
            "form": form,
            "q": q,
        },
    )


@login_required
@staff_required
@require_POST
def manage_media_delete(request, pk):
    _require_user_manager(request)
    asset = get_object_or_404(MediaAsset, pk=pk)
    title = asset.title
    if asset.file:
        asset.file.delete(save=False)
    asset.delete()
    log_action(request, "media.delete", title)
    messages.success(request, f"Asset '{title}' deleted.")
    return redirect("manage_media")


def media_asset_serve(request, pk):
    """Public serving endpoint for marketing media assets."""
    asset = get_object_or_404(MediaAsset, pk=pk)
    if not asset.file:
        raise Http404("Media file not found")
    from django.core.files.storage import FileSystemStorage, default_storage

    if isinstance(default_storage, FileSystemStorage):
        try:
            return FileResponse(asset.file.open("rb"))
        except (FileNotFoundError, ValueError):
            raise Http404("Media file not found")
    return HttpResponseRedirect(asset.file.url)


@login_required
@require_POST
def account_delete(request):
    if request.user.is_admin:
        raise PermissionDenied

    if request.user.has_usable_password():
        if not request.user.check_password(request.POST.get("password", "")):
            messages.error(request, "Password incorrect. Your account was not deleted.")
            return redirect("profile")
    else:
        confirm_email = request.POST.get("confirm_email", "").strip().lower()
        if confirm_email != request.user.email.lower():
            messages.error(request, "Please enter your email address to confirm account deletion.")
            return redirect("profile")

    email = request.user.email
    display_name = request.user.display_name
    _notify_safely(
        "account deletion",
        lambda: send_account_deleted(email, display_name),
    )
    log_action(request, "account.delete", email)
    request.user.delete()
    auth_logout(request)
    messages.success(request, "Your account and data have been permanently deleted.")
    return redirect("home")


@require_http_methods(["GET", "POST"])
def promotional_opt_in_confirm(request, token):
    try:
        uid = signing.TimestampSigner(salt="gctt-promotional-opt-in").unsign(
            token, max_age=PROMOTIONAL_OPT_IN_MAX_AGE
        )
        user = User.objects.filter(pk=int(uid)).first()
    except (signing.BadSignature, ValueError, TypeError):
        user = None

    if user is None or (
        not user.promotional_opt_in
        and not user.promotional_opt_in_requested_at
    ):
        return render(
            request,
            "accounts/promotional_opt_in_confirm.html",
            {"invalid": True},
            status=400,
        )

    if request.method == "POST":
        user.promotional_opt_in = True
        user.promotional_opt_in_at = timezone.now()
        user.promotional_opt_in_requested_at = None
        user.save(
            update_fields=[
                "promotional_opt_in",
                "promotional_opt_in_at",
                "promotional_opt_in_requested_at",
            ]
        )
        messages.success(request, "You can now receive offers and programme news.")
        return redirect("promotional_opt_in_confirm", token=token)

    return render(
        request,
        "accounts/promotional_opt_in_confirm.html",
        {
            "invalid": False,
            "target": user,
            "confirmed": user.promotional_opt_in,
        },
    )


@require_http_methods(["GET", "POST"])
def promotional_unsubscribe(request, token):
    try:
        payload = signing.loads(token, salt="gctt-promotional-unsubscribe")
        user = User.objects.filter(pk=payload.get("uid")).first()
    except (signing.BadSignature, ValueError, TypeError, AttributeError):
        user = None

    if user is None:
        return render(
            request,
            "accounts/unsubscribe.html",
            {"invalid": True},
            status=400,
        )

    if request.method == "POST":
        user.promotional_opt_in = False
        user.promotional_opt_in_requested_at = None
        user.save(
            update_fields=[
                "promotional_opt_in",
                "promotional_opt_in_requested_at",
            ]
        )
        messages.success(request, "You have been removed from promotional emails.")
        return redirect("promotional_unsubscribe", token=token)

    return render(
        request,
        "accounts/unsubscribe.html",
        {"invalid": False, "target": user, "unsubscribed": not user.promotional_opt_in},
    )


@csrf_exempt
@require_POST
@ratelimit(key="ip", rate="30/m", method="POST", block=True)
def promotional_unsubscribe_one_click(request, token):
    """RFC 8058 one-click unsubscribe target for mailbox providers."""
    try:
        payload = signing.loads(token, salt="gctt-promotional-unsubscribe")
        user = User.objects.filter(pk=payload.get("uid")).first()
    except (signing.BadSignature, ValueError, TypeError, AttributeError):
        user = None

    if user is None:
        return HttpResponse("invalid unsubscribe token", status=400)

    user.promotional_opt_in = False
    user.promotional_opt_in_requested_at = None
    user.save(
        update_fields=[
            "promotional_opt_in",
            "promotional_opt_in_requested_at",
        ]
    )
    return HttpResponse("unsubscribed", status=200)


@login_required
def security(request):
    return render(
        request,
        "accounts/security.html",
        {
            "email_otp_required": (
                settings.REQUIRE_EMAIL_OTP and request.user.requires_email_otp
            ),
        },
    )
