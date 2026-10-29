"""Redact credentials in error reports even in a local DEBUG environment."""

from django.conf import settings
from django.views.debug import SafeExceptionReporterFilter

SECRET_FIELDS = (
    "password",
    "old_secret",
    "new_secret",
    "confirmation",
    "cf-turnstile-response",
    "website",
)


class SecurityExceptionReporterFilter(SafeExceptionReporterFilter):
    def is_active(self, request):
        return True

    def cleanse_setting(self, key, value):
        if key == "CANARY_HTTP_TOKEN_URL":
            return self.cleansed_substitute
        if key in (settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME):
            return self.cleansed_substitute
        return super().cleanse_setting(key, value)

    def get_post_parameters(self, request):
        params = super().get_post_parameters(request).copy()
        for name in SECRET_FIELDS:
            if name in params:
                params[name] = self.cleansed_substitute
        return params

    def get_cleansed_multivaluedict(self, request, multivaluedict):
        values = super().get_cleansed_multivaluedict(request, multivaluedict).copy()
        for name in SECRET_FIELDS:
            if name in values:
                values[name] = self.cleansed_substitute
        return values
