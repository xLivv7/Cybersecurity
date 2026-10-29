"""Bounded Siteverify validation and atomic single-use token redemption."""

import hashlib
import json
from datetime import datetime, timedelta
from urllib.error import URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings
from django.db import OperationalError, transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from .models import CaptchaRedemption

TOKEN_FIELD = "cf-turnstile-response"
CAPTCHA_ERROR = (
    "Weryfikacja CAPTCHA nie powiodła się. Wykonaj nowe wyzwanie i spróbuj ponownie."
)
CONFIG_ERROR = (
    "Weryfikacja CAPTCHA jest niedostępna. Sprawdź konfigurację lub spróbuj później."
)
ACTIONS = frozenset({"login", "password_change", "password_required"})


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def configured(hostname):
    return bool(
        settings.TURNSTILE_SITE_KEY
        and settings.TURNSTILE_SECRET_KEY
        and hostname in settings.TURNSTILE_ALLOWED_HOSTNAMES
    )


def widget_context(request, action):
    host = urlsplit("//" + request.get_host()).hostname
    return {
        "captcha_action": action,
        "captcha_site_key": settings.TURNSTILE_SITE_KEY if configured(host) else "",
        "captcha_config_error": CONFIG_ERROR,
    }


@sensitive_variables()
def _siteverify(token):
    body = urlencode(
        {"secret": settings.TURNSTILE_SECRET_KEY, "response": token}
    ).encode()
    request = Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with build_opener(NoRedirect()).open(request, timeout=5) as response:
        if response.status != 200:
            return None
        raw = response.read(16385)
    return json.loads(raw) if len(raw) <= 16384 else None


@sensitive_variables()
def validate_token(token, *, action, hostname):
    if (
        action not in ACTIONS
        or not configured(hostname)
        or not isinstance(token, str)
        or not 0 < len(token) <= 2048
    ):
        return False
    digest = hashlib.sha256(token.encode()).hexdigest()
    try:
        if CaptchaRedemption.objects.filter(token_digest=digest).exists():
            return False
        result = _siteverify(token)
        if (
            not isinstance(result, dict)
            or result.get("success") is not True
            or result.get("hostname") != hostname
            or result.get("action") != action
            or not isinstance(result.get("challenge_ts"), str)
        ):
            return False
        issued = datetime.fromisoformat(result["challenge_ts"])
        now = timezone.now()
        if timezone.is_naive(issued) or not issued <= now < issued + timedelta(
            seconds=300
        ):
            return False
        with transaction.atomic():
            CaptchaRedemption.objects.filter(expires_at__lte=now).delete()
            _, created = CaptchaRedemption.objects.get_or_create(
                token_digest=digest,
                defaults={"expires_at": issued + timedelta(seconds=300)},
            )
        return created
    except (URLError, OSError, ValueError, TypeError, OverflowError, OperationalError):
        return False


@sensitive_variables()
def validate_request(request, action):
    tokens = request.POST.getlist(TOKEN_FIELD)
    host = urlsplit("//" + request.get_host()).hostname
    return len(tokens) == 1 and validate_token(tokens[0], action=action, hostname=host)
