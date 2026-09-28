"""Test Django settings for jolarca-consent."""

import os

# Must be set BEFORE importing base: base.py fails closed when
# DJANGO_SECRET_KEY is absent (audit finding A-07). This value is a throwaway
# for the test suite only. It is published in this repository and must never be used
# by an environment that serves traffic.
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-insecure-throwaway-not-a-real-secret")

from .base import *  # noqa: F403

DEBUG = False

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# Use SQLite for tests (faster than PostgreSQL)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
