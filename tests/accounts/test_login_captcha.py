"""Real login gates with a mocked provider; no regression auto-token fixture."""

from unittest.mock import Mock

import pytest
from django.test import Client
from django.utils import timezone

from apps.security import captcha, login_limits
from apps.security.models import CaptchaRedemption, LoginAttemptState, SecurityEvent
from apps.security.selectors import get_security_settings
from apps.security.sessions import CONTEXT_KEY

pytestmark = pytest.mark.django_db
PASSWORD = "previous long passphrase"


@pytest.fixture
def provider(settings, monkeypatch):
    settings.TURNSTILE_SITE_KEY = "public-site"
    settings.TURNSTILE_SECRET_KEY = "private-secret"
    settings.TURNSTILE_ALLOWED_HOSTNAMES = ["testserver"]
    mock = Mock(
        side_effect=lambda token: {
            "success": token == "valid-token",
            "hostname": "testserver",
            "action": "login",
            "challenge_ts": timezone.now().isoformat(),
        }
    )
    monkeypatch.setattr(captcha, "_siteverify", mock)
    return mock


@pytest.mark.parametrize("token", [None, "", "invalid"])
def test_missing_and_invalid_tokens_never_check_password(
    token, provider, user_factory, client, monkeypatch
):
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    verify = Mock(side_effect=AssertionError("Password must not be checked"))
    monkeypatch.setattr(login_limits, "authenticate_login", verify)
    data = {"login": "reader", "password": PASSWORD}
    if token is not None:
        data[captcha.TOKEN_FIELD] = token
    response = client.post("/login/", data)
    assert response.status_code == 200 and captcha.CAPTCHA_ERROR in response.text
    assert CONTEXT_KEY not in client.session
    assert not LoginAttemptState.objects.exists()
    assert SecurityEvent.objects.get().category == "captcha_rejected"
    assert PASSWORD not in response.text
    assert "private-secret" not in response.text
    assert 'data-action="login"' in response.text
    verify.assert_not_called()


def test_honeypot_precedes_provider_and_password(provider, client, monkeypatch):
    verify = Mock(side_effect=AssertionError("Password must not be checked"))
    monkeypatch.setattr(login_limits, "authenticate_login", verify)
    response = client.post(
        "/login/",
        {
            "login": "reader",
            "password": PASSWORD,
            "website": "bot-value",
            captcha.TOKEN_FIELD: "valid-token",
        },
    )
    assert response.status_code == 200
    assert SecurityEvent.objects.get().category == "honeypot"
    provider.assert_not_called()
    verify.assert_not_called()
    assert not LoginAttemptState.objects.exists()
    assert "bot-value" in response.text  # hidden form data is not a credential
    assert 'type="hidden" name="website"' in response.text
    assert 'autocomplete="off"' in response.text


def test_block_precedes_provider_and_success_replay_fails(
    provider, user_factory, client, clock
):
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    data = {"login": "reader", "password": PASSWORD, captcha.TOKEN_FIELD: "valid-token"}
    assert client.post("/login/", data).status_code == 302
    assert CaptchaRedemption.objects.count() == 1
    client.post("/logout/")
    response = client.post("/login/", data)
    assert captcha.CAPTCHA_ERROR in response.text
    assert LoginAttemptState.objects.get().failure_count == 0
    assert provider.call_count == 1  # local replay protection avoids another call
    policy = get_security_settings()
    policy.login_failure_limit = 1
    policy.save()
    # A fresh token authorizes a wrong password and triggers the limit.
    provider.side_effect = lambda token: {
        "success": True,
        "hostname": "testserver",
        "action": "login",
        "challenge_ts": clock.now().isoformat(),
    }
    data.update(password="wrong", **{captcha.TOKEN_FIELD: "fresh"})
    client.post("/login/", data)
    calls = provider.call_count
    data[captcha.TOKEN_FIELD] = "not-used-while-blocked"
    response = client.post("/login/", data)
    assert response.context["login_block_seconds"] == 900
    assert provider.call_count == calls


def test_csrf_precedes_all_gates(provider):
    response = Client(enforce_csrf_checks=True).post(
        "/login/", {"login": "reader", "password": PASSWORD, "website": "bot"}
    )
    assert response.status_code == 403
    provider.assert_not_called()
    assert not SecurityEvent.objects.exists()


def test_configuration_failure_visible_and_token_not_reflected(settings, client):
    settings.TURNSTILE_SECRET_KEY = ""
    token = "private-captcha-input"
    response = client.post(
        "/login/", {"login": "reader", "password": PASSWORD, captcha.TOKEN_FIELD: token}
    )
    assert captcha.CONFIG_ERROR in response.text
    assert "challenges.cloudflare.com/turnstile/v0/api.js" not in response.text
    assert token not in response.text
