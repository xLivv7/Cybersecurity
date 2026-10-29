"""HTTPS deployment settings; configuration must be provided by the environment."""

from django.core.exceptions import ImproperlyConfigured

from ._env import hosts_from_environment, secret_key_from_environment
from ._turnstile import configuration
from .base import *  # noqa: F403

SECRET_KEY = secret_key_from_environment()
ALLOWED_HOSTS = hosts_from_environment()
if not ALLOWED_HOSTS or any("*" in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "Ustaw DJANGO_ALLOWED_HOSTS na jawną listę hostów bez znaku *."
    )

DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Trust proxy headers only after the actual deployment topology is configured.
TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY, TURNSTILE_ALLOWED_HOSTNAMES = configuration(
    production=True
)
