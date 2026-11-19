import hashlib
import secrets
from datetime import timedelta

from django.utils import timezone

PENDING_TTL = timedelta(hours=24)


def make_token():
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def expiry():
    return timezone.now() + PENDING_TTL
