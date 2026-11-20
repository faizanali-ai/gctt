from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


def is_verified(user):
    """TOTP verification state installed by django_otp's middleware."""
    return bool(getattr(user, "is_verified", lambda: False)())


def needs_staff_2fa(user):
    return bool(
        settings.REQUIRE_STAFF_2FA
        and user.is_authenticated
        and user.is_staff
        and not getattr(user, "is_admin", False)
        and not is_verified(user)
    )


def staff_2fa_redirect(request):
    """Return the enrollment redirect for an unverified internal user, else None."""
    if needs_staff_2fa(request.user):
        return redirect(f"{reverse('security')}?next={quote(request.get_full_path())}")
    return None


def staff_required(view):
    """Require an active internal account, plus 2FA when it is enforced."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not (user.is_authenticated and user.is_active and user.is_staff):
            raise PermissionDenied
        blocked = staff_2fa_redirect(request)
        if blocked:
            return blocked
        return view(request, *args, **kwargs)

    return wrapper


def verified_staff_required(view):
    """For mixed-audience views: unverified internal users are sent to enrollment."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        blocked = staff_2fa_redirect(request)
        if blocked:
            return blocked
        return view(request, *args, **kwargs)

    return wrapper
