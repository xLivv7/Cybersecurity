"""Explicit environment configuration, without a verification bypass."""

import os

from django.core.exceptions import ImproperlyConfigured

TEST_SITE_KEYS = frozenset(
    {
        "1x00000000000000000000AA",
        "2x00000000000000000000AB",
        "1x00000000000000000000BB",
        "2x00000000000000000000BB",
        "3x00000000000000000000FF",
    }
)
TEST_SECRET_KEYS = frozenset(
    {
        "1x0000000000000000000000000000000AA",
        "2x0000000000000000000000000000000AA",
        "3x0000000000000000000000000000000AA",
    }
)


def configuration(*, production=False):
    site = os.environ.get("TURNSTILE_SITE_KEY", "").strip()
    secret = os.environ.get("TURNSTILE_SECRET_KEY", "").strip()
    hosts = [
        h.strip().lower()
        for h in os.environ.get("TURNSTILE_ALLOWED_HOSTNAMES", "").split(",")
        if h.strip()
    ]
    valid = bool(site and secret and hosts) and all(
        not any(c in host for c in "*/:?# ") for host in hosts
    )
    if production and (
        not valid or site in TEST_SITE_KEYS or secret in TEST_SECRET_KEYS
    ):
        raise ImproperlyConfigured(
            "Ustaw TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY i TURNSTILE_ALLOWED_HOSTNAMES; produkcja wymaga rzeczywistych kluczy i jawnych hostów."
        )
    return site, secret, hosts
