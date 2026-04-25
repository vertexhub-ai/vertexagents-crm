"""
Minimal Django settings for the CRM.

V-167 (full bootstrap: Docker, Tailwind, HTMX, axes, Sentry, etc.) is still in flight;
this settings module is the slimmest thing that lets V-169 schema + migrations land.
Everything not strictly required for `manage.py migrate` / `pytest` is intentionally absent.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-not-for-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "accounts",
    "crm",
]

MIDDLEWARE: list[str] = []

ROOT_URLCONF = "config.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "crm"),
        "USER": os.environ.get("POSTGRES_USER", "crm"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "crm"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# SQLite is used for unit tests that don't exercise Postgres-specific constraints.
# Postgres-only tests are decorated with @pytest.mark.skipif on connection.vendor.
if os.environ.get("DJANGO_TEST_SQLITE") == "1":
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }

AUTH_USER_MODEL = "accounts.User"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
