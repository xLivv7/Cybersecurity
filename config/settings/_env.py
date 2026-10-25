"""Read shared settings without loading local files."""

import os

from django.core.exceptions import ImproperlyConfigured


def secret_key_from_environment():
    key = os.environ.get("DJANGO_SECRET_KEY", "")
    if len(key) < 50 or len(set(key)) < 5 or key.startswith("django-insecure-"):
        raise ImproperlyConfigured(
            "Ustaw DJANGO_SECRET_KEY: co najmniej 50 znaków i 5 różnych znaków, "
            "bez prefiksu django-insecure-. Lokalnie możesz użyć pliku .env."
        )
    return key


def hosts_from_environment(default=""):
    return [
        host.strip()
        for host in os.environ.get("DJANGO_ALLOWED_HOSTS", default).split(",")
        if host.strip()
    ]
