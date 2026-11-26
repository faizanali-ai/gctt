import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import EmailOTP


def _email(value):
    return (value or "").strip().lower()


def _resend_key(email):
    return f"email-otp-issue:{email}"


def clear_issue_cooldown(email):
    cache.delete(_resend_key(_email(email)))


def issue_code(email):
    """Create a single active OTP for an email. Returns (otp, raw_code) or None."""
    email = _email(email)
    if not email:
        return None

    cooldown = int(getattr(settings, "EMAIL_OTP_RESEND_SECONDS", 60))
    if not cache.add(_resend_key(email), True, cooldown):
        return None

    code = f"{secrets.randbelow(1_000_000):06d}"
    now = timezone.now()
    EmailOTP.objects.filter(email=email, consumed_at__isnull=True).update(
        consumed_at=now
    )
    otp = EmailOTP.objects.create(
        email=email,
        code_hash=make_password(code),
        expires_at=now
        + timedelta(seconds=int(getattr(settings, "EMAIL_OTP_TTL_SECONDS", 300))),
    )
    return otp, code


def verify_code(email, code):
    """Consume a valid OTP. Invalid, expired, used, or exhausted codes return False."""
    email = _email(email)
    code = (code or "").strip()
    now = timezone.now()
    with transaction.atomic():
        otp = (
            EmailOTP.objects.select_for_update()
            .filter(email=email, consumed_at__isnull=True, expires_at__gt=now)
            .order_by("-created_at")
            .first()
        )
        if otp is None:
            return False

        max_attempts = int(getattr(settings, "EMAIL_OTP_MAX_ATTEMPTS", 5))
        if otp.attempts >= max_attempts:
            otp.consumed_at = now
            otp.save(update_fields=["consumed_at"])
            return False

        if check_password(code, otp.code_hash):
            otp.consumed_at = now
            otp.save(update_fields=["consumed_at"])
            return True

        otp.attempts += 1
        if otp.attempts >= max_attempts:
            otp.consumed_at = now
        otp.save(update_fields=["attempts", "consumed_at"])
        return False


def purge_expired():
    """Delete expired or consumed OTP rows. Returns the deleted count."""
    deleted, _ = EmailOTP.objects.filter(
        Q(expires_at__lt=timezone.now()) | Q(consumed_at__isnull=False)
    ).delete()
    return deleted
