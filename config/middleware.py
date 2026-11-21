import secrets

from django.contrib.auth import logout
from django.http import HttpResponseGone, JsonResponse
from django.shortcuts import redirect
from django.urls import Resolver404, resolve
from django.utils import timezone

from .legacy import LEGACY_URL_NAMES, SUNSET_DATE, SUNSET_HTTP


class ActiveUserMiddleware:
    """End access for an account deactivated while its session is still open.

    Django authenticates a session from the stored user id and does not re-check
    ``is_active`` on every request. Admin deactivation must revoke access
    immediately, including candidate/student PII.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_active:
            logout(request)
            if request.path.startswith("/api/") or request.path.startswith("/enquiries/"):
                return JsonResponse({"error": "account inactive"}, status=403)
            return redirect("login")
        return self.get_response(request)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        response["X-Frame-Options"] = "DENY"
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{request.csp_nonce}'; "
            f"style-src 'self' 'nonce-{request.csp_nonce}'; "
            "font-src 'self' data:; "
            "img-src 'self' data: https:; "
            "frame-ancestors 'none';"
        )
        if getattr(request, "user", None) and request.user.is_authenticated:
            response["Cache-Control"] = "no-store"
        return response


class LegacyUrlSunsetMiddleware:
    """Deprecate the four numeric legacy routes, then return 410 after sunset."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            match = resolve(request.path_info)
        except Resolver404:
            match = None
        if match is None or match.url_name not in LEGACY_URL_NAMES:
            return self.get_response(request)

        if timezone.localdate() >= SUNSET_DATE:
            return HttpResponseGone("This URL has been retired.")
        response = self.get_response(request)
        response["Deprecation"] = "true"
        response["Sunset"] = SUNSET_HTTP
        return response
