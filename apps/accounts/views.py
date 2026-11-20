import json
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
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.tokens import email_verification_token_generator
from apps.enquiries.models import Enquiry
from apps.jobs.models import Application, Job
from apps.training.models import Programme, Registration
from config.emails import send_login_otp, send_password_setup, send_verification

from .audit import log_action
from .decorators import staff_required
from .email_otp import issue_code, verify_code
from .forms import ProfileForm, SignupForm, StyledAuthenticationForm
from .models import STAFF_SUBGROUPS, User, sync_access

INPUT = "w-full rounded-sm border border-line bg-white px-4 py-2.5"


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
            try:
                user = form.save()
            except IntegrityError:
                messages.info(
                    request, "If this email can be used, check your inbox to continue."
                )
                return redirect("login")
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
        if user.is_staff and settings.REQUIRE_EMAIL_OTP:
            return _start_email_otp(
                self.request, user, self.get_success_url()
            )
        return super().form_valid(form)


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
            log_action(request, "auth.email_otp_send_failed", _mask_email(email))

    messages.info(
        request,
        "If this email can be used, check your inbox for a sign-in code.",
    )
    return redirect("email_otp_verify")


def _complete_email_otp_login(request, user):
    next_url = request.session.pop("email_otp_next", None)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
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

        user = User.objects.filter(
            email__iexact=email, is_active=True, is_staff=True
        ).first()
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
            user = User.objects.filter(
                email__iexact=email, is_active=True
            ).first()
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

    user = User.objects.filter(
        email__iexact=email, is_active=True, is_staff=True
    ).first()
    if user:
        issued = issue_code(email)
        if issued:
            if send_login_otp(email, issued[1]):
                log_action(request, "auth.email_otp_resend", email)
            else:
                log_action(
                    request, "auth.email_otp_send_failed", _mask_email(email)
                )

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

        if user.is_staff and settings.REQUIRE_EMAIL_OTP:
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
    elif user and (
        email_verification_token_generator.check_token(user, token)
        or default_token_generator.check_token(user, token)
    ):
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
        form.save()
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
    users = User.objects.filter(is_staff=True).select_related()
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
            "roles": User.Role.choices,
        },
    )


@login_required
@staff_required
def manage_user_create(request):
    _require_user_manager(request)
    assignable = request.user.assignable_roles()
    subgroups = Group.objects.filter(name__in=STAFF_SUBGROUPS)
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        role = request.POST.get("role", "")
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        subgroup = request.POST.get("group", "")
        password = request.POST.get("password", "")
        error = None
        if role not in [value for value, _ in assignable]:
            error = "You cannot assign that role."
        elif role == User.Role.STAFF and subgroup not in STAFF_SUBGROUPS:
            error = "Select a valid staff subgroup."
        elif not email:
            error = "Email is required."
        elif User.objects.filter(email__iexact=email).exists():
            error = "A user with that email already exists."
        else:
            try:
                validate_password(password)
            except ValidationError as exc:
                error = " ".join(exc.messages)
        if error:
            messages.error(request, error)
        else:
            try:
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    is_staff=True,
                )
                sync_access(user, subgroup if role == User.Role.STAFF else None)
            except IntegrityError:
                messages.error(request, "A user with that email already exists.")
                return render(
                    request,
                    "portals/user_form.html",
                    {
                        "mode": "create",
                        "assignable": assignable,
                        "groups": subgroups,
                    },
                )
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
            "groups": subgroups,
        },
    )


@login_required
@staff_required
def manage_user_edit(request, pk):
    _require_user_manager(request)
    target = get_object_or_404(User.objects.filter(is_staff=True), pk=pk)
    if not request.user.can_manage_account(target):
        raise PermissionDenied
    assignable = request.user.assignable_roles()
    subgroups = Group.objects.filter(name__in=STAFF_SUBGROUPS)
    current_subgroup = target.groups.filter(name__in=STAFF_SUBGROUPS).values_list(
        "name", flat=True
    ).first()
    if request.method == "POST":
        role = request.POST.get("role", target.role)
        subgroup = request.POST.get("group", current_subgroup or "")
        is_active = request.POST.get("is_active") == "on"
        error = None
        if role not in [value for value, _ in assignable]:
            error = "You cannot assign that role."
        elif role == User.Role.STAFF and subgroup not in STAFF_SUBGROUPS:
            error = "Select a valid staff subgroup."
        elif target == request.user and role != User.Role.ADMIN:
            error = "You cannot change your own admin role."
        elif target == request.user and not is_active:
            error = "You cannot deactivate your own account."
        elif target.is_admin and (role != User.Role.ADMIN or not is_active) and _active_admin_count() <= 1:
            error = "You cannot remove the last active admin."
        if error:
            messages.error(request, error)
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
                            "groups": subgroups,
                        },
                    )
            target.first_name = request.POST.get("first_name", "").strip()
            target.last_name = request.POST.get("last_name", "").strip()
            target.phone = request.POST.get("phone", "").strip()
            target.role = role
            target.is_active = is_active
            target.is_staff = True
            target.save()
            sync_access(target, subgroup if role == User.Role.STAFF else None)
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
            "groups": subgroups,
        },
    )


@login_required
@staff_required
@require_POST
def manage_user_delete(request, pk):
    _require_user_manager(request)
    target = get_object_or_404(User.objects.filter(is_staff=True), pk=pk)
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
    log_action(request, "account.delete", email)
    request.user.delete()
    auth_logout(request)
    messages.success(request, "Your account and data have been permanently deleted.")
    return redirect("home")


@login_required
def security(request):
    return render(
        request,
        "accounts/security.html",
        {
            "email_otp_required": (
                settings.REQUIRE_EMAIL_OTP and request.user.is_staff
            ),
        },
    )
