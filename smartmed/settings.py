"""
Django settings for the SmartMed project.

Phase 1 scope: project skeleton, all core models, authentication (custom User
model + DRF token auth), RBAC groundwork. Later phases add ML, OCR, maps.
"""
from pathlib import Path
from datetime import timedelta

from .env import load_env, env_bool, env_list

BASE_DIR = Path(__file__).resolve().parent.parent

load_env(BASE_DIR / ".env")

import os  # noqa: E402  (after load_env on purpose)

# ---------------------------------------------------------------------------
# Core / security
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-dev-only-change-me-before-any-real-deployment",
)
DEBUG = env_bool("DEBUG", default=True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis" if env_bool("USE_GIS", default=False) else None,
]
DJANGO_APPS = [app for app in DJANGO_APPS if app]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
]

LOCAL_APPS = [
    "accounts",
    "medicines",
    "pharmacies",
    "inventory",
    "prescriptions",
    "alternatives",
    "predictions",
    "dashboard",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "smartmed.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "smartmed.wsgi.application"
ASGI_APPLICATION = "smartmed.asgi.application"

# ---------------------------------------------------------------------------
# Database
#   Default: SQLite (zero-setup for local dev / grading).
#   Optional: PostgreSQL via DATABASE_URL, e.g.
#     postgres://user:password@localhost:5432/smartmed
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL.startswith("postgres"):
    import re

    m = re.match(
        r"postgres(?:ql)?://(?P<user>[^:]+):(?P<password>[^@]*)@"
        r"(?P<host>[^:/]+):?(?P<port>\d*)/(?P<name>.+)",
        DATABASE_URL,
    )
    if not m:
        raise ValueError(
            "DATABASE_URL is set but could not be parsed. Expected format: "
            "postgres://user:password@host:port/dbname"
        )
    gd = m.groupdict()
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": gd["name"],
            "USER": gd["user"],
            "PASSWORD": gd["password"],
            "HOST": gd["host"],
            "PORT": gd["port"] or "5432",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "accounts:login"

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "120/minute",
    },
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "EXCEPTION_HANDLER": "smartmed.exceptions.custom_exception_handler",
}

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / media files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Prescription uploads live under a non-guessable, non-listable subpath.
# Access is mediated entirely through authenticated, owner-checked views —
# see prescriptions/views.py. This directory is never served directly by
# a public StaticFiles/MEDIA route in production (see README deployment notes).
PRESCRIPTION_UPLOAD_SUBDIR = "prescriptions"
PRESCRIPTION_MAX_UPLOAD_MB = int(os.environ.get("PRESCRIPTION_MAX_UPLOAD_MB", "5"))
PRESCRIPTION_ALLOWED_CONTENT_TYPES = [
    "image/jpeg",
    "image/png",
]
PRESCRIPTION_RETENTION_DAYS = int(os.environ.get("PRESCRIPTION_RETENTION_DAYS", "30"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# External service configuration (adapters read these; see ml/, later phases)
# ---------------------------------------------------------------------------
OCR_PATH = os.environ.get("OCR_PATH", "")  # path to tesseract binary, if non-default
MAP_PROVIDER = os.environ.get("MAP_PROVIDER", "osm")  # osm | (future: paid provider)
GEOCODING_PROVIDER = os.environ.get("GEOCODING_PROVIDER", "nominatim")
DEMO_MODE = env_bool("DEMO_MODE", default=True)

# ---------------------------------------------------------------------------
# Security hardening
# ---------------------------------------------------------------------------
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # must be readable by JS for AJAX CSRF header
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ---------------------------------------------------------------------------
# Logging (never log raw prescription text / PII — see prescriptions app)
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "smartmed": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
