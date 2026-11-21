import secrets

from django.http import HttpResponseGone
from django.urls import Resolver404, resolve
from django.utils import timezone

from .legacy import LEGACY_URL_NAMES, SUNSET_DATE, SUNSET_HTTP


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
