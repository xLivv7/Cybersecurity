"""Read current policy once per call, without hiding missing initialization."""

from .models import SecuritySettings


def get_security_settings():
    return SecuritySettings.objects.get(pk=1)
