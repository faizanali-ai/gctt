"""Cached access to the editable site identity.

A short process-local cache keeps ordinary page views off the database. The
cache is deliberately not the Django cache backend: the production cache is
database-backed, and a database round trip here would defeat the purpose.
"""

from __future__ import annotations

import time
from urllib.parse import urlparse

from django.conf import settings
from django.db import DatabaseError

from apps.accounts.models import SiteSettings
from config.constants import COMPANY

_CACHE: dict[str, object] = {"value": None, "expires_at": 0.0}


def _ttl() -> int:
    return int(getattr(settings, "SITE_SETTINGS_CACHE_SECONDS", 30))


def clear_company_cache() -> None:
    _CACHE["value"] = None
    _CACHE["expires_at"] = 0.0


def company() -> dict[str, str]:
    """Company identity with database values merged over the constants."""
    now = time.monotonic()
    cached = _CACHE["value"]
    if cached is not None and now < float(_CACHE["expires_at"]):
        return dict(cached)  # type: ignore[arg-type]

    merged = dict(COMPANY)
    try:
        record = SiteSettings.load()
    except DatabaseError:
        return merged

    for key, value in (
        ("name", record.company_name),
        ("legal_name", record.legal_name),
        ("tagline", record.tagline),
        ("email", record.email),
        ("jobs_email", record.jobs_email),
        ("address", record.address),
        ("url", record.url.rstrip("/")),
    ):
        if value:
            merged[key] = value
    merged["jobsEmail"] = merged["jobs_email"]
    merged["domain"] = urlparse(merged["url"]).netloc or COMPANY["domain"]
    merged.update(
        {
            "hero_eyebrow": record.hero_eyebrow,
            "hero_title": record.hero_title,
            "hero_subtitle": record.hero_subtitle,
            "hero_cta_label": record.hero_cta_label,
            "hero_cta_url": record.hero_cta_url,
        }
    )
    _CACHE["value"] = merged
    _CACHE["expires_at"] = now + _ttl()
    return dict(merged)
