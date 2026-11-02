"""Settings for pytest. Works without .env values; CI and the container pass DATABASE_URL (PostgreSQL)."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-a-secret")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")

from .dev import *  # noqa: F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
