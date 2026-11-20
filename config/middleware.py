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
    """Default-deny for unverified internal users when 2FA is enforced.

    Only active when REQUIRE_STAFF_2FA is on. Candidates, students, and
    admins are unaffected; admins use email OTP only. Unverified staff may
    only reach logout and enrollment/verification endpoints; everything else
    redirects to /accounts/security/.
    """

    ALLOWED_PREFIXES = (
        "/accounts/login/",
        "/accounts/logout/",
        "/accounts/google/",
        "/accounts/security/",
        "/accounts/verify/",
        "/accounts/password-reset/",
        "/static/",
        "/media/",
        "/healthz/",
        "/health/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if (
            settings.REQUIRE_STAFF_2FA
            and user.is_authenticated
            and user.is_staff
            and not getattr(user, "is_admin", False)
            and not getattr(user, "is_verified", lambda: False)()
            and not request.path.startswith(self.ALLOWED_PREFIXES)
        ):
            from urllib.parse import quote

            from django.urls import reverse

            next_url = quote(request.get_full_path())
            return redirect(f"{reverse('security')}?next={next_url}")
        return self.get_response(request)
