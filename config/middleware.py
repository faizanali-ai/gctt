from django.conf import settings
from django.shortcuts import redirect


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Frame-Options"] = "DENY"
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # shortcut: 'unsafe-inline' kept for inline toast/script snippets, tighten with nonces later
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "frame-ancestors 'none';"
        )
        return response


class StaffTwoFactorMiddleware:
    """Blocks staff pages until the session is verified with a TOTP device.

    Only active when REQUIRE_STAFF_2FA is on, so accounts can enrol first.
    """

    PROTECTED_PREFIXES = ("/admin/", "/staff/", "/dashboard/", "/profile/", "/manage/")
    ALLOWED_PREFIXES = ("/accounts/", "/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.REQUIRE_STAFF_2FA
            and request.user.is_authenticated
            and request.user.is_staff
            and not getattr(request.user, "is_verified", lambda: False)()
            and request.path.startswith(self.PROTECTED_PREFIXES)
            and not request.path.startswith(self.ALLOWED_PREFIXES)
        ):
            return redirect("security")
        return self.get_response(request)
