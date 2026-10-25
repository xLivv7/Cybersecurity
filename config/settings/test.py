"""Isolated test settings that never load .env or open the local database."""

from django.core.management.utils import get_random_secret_key

from .base import *  # noqa: F403

SECRET_KEY = get_random_secret_key()
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1", "[::1]"]
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "ATOMIC_REQUESTS": False,
        "OPTIONS": {
            "transaction_mode": "IMMEDIATE",
            "timeout": 5,
        },
    },
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
