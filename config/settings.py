import os
import sys
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

TESTING = "test" in sys.argv

# Safe default: debug is OFF unless explicitly enabled for local development.
DEBUG = os.environ.get("DJANGO_DEBUG", "").lower() in ("1", "true", "yes")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
if not DEBUG and not TESTING and SECRET_KEY.startswith("dev-only"):
    raise RuntimeError("Set DJANGO_SECRET_KEY before running with DJANGO_DEBUG off")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "apps.accounts",
    "apps.jobs",
    "apps.training",
    "apps.enquiries",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DEBUG and not TESTING and not DATABASE_URL:
    # Never fall back to ephemeral SQLite in production.
    raise RuntimeError("DATABASE_URL is required when DJANGO_DEBUG is off")

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=600
    )
}

# Rate-limit keys use the real client IP behind the platform proxy.
if not DEBUG and not TESTING:
    RATELIMIT_IP_META_KEY = "HTTP_X_FORWARDED_FOR"

# Shared cache for rate-limit counters: Redis when provided, database cache in
# production (multiple workers), per-process memory in local development.
REDIS_URL = os.environ.get("REDIS_URL", "")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
elif not DEBUG and not TESTING:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "ratelimit_cache",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Cloudflare R2 (S3-compatible) when configured. Bucket stays private; media
# URLs are time-signed so resumes are not publicly readable.
if os.environ.get("R2_BUCKET"):
    AWS_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
    AWS_STORAGE_BUCKET_NAME = os.environ["R2_BUCKET"]
    AWS_S3_ENDPOINT_URL = os.environ["R2_ENDPOINT"]
    AWS_S3_REGION_NAME = "auto"
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 600
    AWS_S3_FILE_OVERWRITE = False
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Accounts@gctekton.com")
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 10

if not DEBUG and not TESTING:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
