"""Development Django settings for jolarca-consent."""

import os

# Must be set BEFORE importing base: base.py fails closed when
# DJANGO_SECRET_KEY is absent (audit finding A-07). This value is a throwaway
# for local development only. It is published in this repository and must never be used
# by an environment that serves traffic.
os.environ.setdefault("DJANGO_SECRET_KEY", "dev-only-insecure-throwaway-not-a-real-secret")

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Use SQLite for development to avoid PostgreSQL dependency during dev
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "db.sqlite3"),  # noqa: F405
    }
}
