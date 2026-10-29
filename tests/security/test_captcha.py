"""Offline contract tests exercise the real adapter and redemption ledger."""

from datetime import timedelta
from unittest.mock import MagicMock
from urllib.error import URLError
from urllib.parse import parse_qs

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory

from apps.security import captcha
from apps.security.models import CaptchaRedemption
from apps.security.reporting import SecurityExceptionReporterFilter
from config.settings._turnstile import TEST_SECRET_KEYS, TEST_SITE_KEYS, configuration

pytestmark = pytest.mark.django_db


@pytest.fixture
def configured_captcha(settings):
    settings.TURNSTILE_SITE_KEY = "configured-site"
    settings.TURNSTILE_SECRET_KEY = "private-server-secret"
    settings.TURNSTILE_ALLOWED_HOSTNAMES = ["testserver"]


def success(clock, **changes):
    return {
        "success": True,
        "hostname": "testserver",
        "action": "login",
        "challenge_ts": clock.now().isoformat(),
        **changes,
    }


def check(token="opaque-captcha-token"):
    return captcha.validate_token(token, action="login", hostname="testserver")


def test_success_redemption_replay_and_expired_cleanup(
    configured_captcha, clock, monkeypatch
):
    monkeypatch.setattr(captcha, "_siteverify", lambda token: success(clock))
    assert check()
    assert not check()
    row = CaptchaRedemption.objects.get()
    assert row.token_digest != "opaque-captcha-token" and len(row.token_digest) == 64
    clock.advance(timedelta(seconds=300))
    assert check("another-fresh-token")
    assert not CaptchaRedemption.objects.filter(pk=row.pk).exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"success": False},
        {"success": "true"},
        {"hostname": "other"},
        {"action": "password_required"},
        {"challenge_ts": "invalid"},
        {"challenge_ts": "2026-01-01T00:00:00"},
        {"challenge_ts": None},
    ],
)
def test_invalid_response_is_rejected(changes, configured_captcha, clock, monkeypatch):
    monkeypatch.setattr(captcha, "_siteverify", lambda token: success(clock, **changes))
    assert not check()
    assert not CaptchaRedemption.objects.exists()


@pytest.mark.parametrize(
    "result",
    [None, [], True, {}, {"success": False, "error-codes": ["timeout-or-duplicate"]}],
)
def test_malformed_or_duplicate_response(result, configured_captcha, monkeypatch):
    monkeypatch.setattr(captcha, "_siteverify", lambda token: result)
    assert not check()


@pytest.mark.parametrize(
    "age,allowed", [(299.999999, True), (300, False), (300.000001, False), (-1, False)]
)
def test_exact_provider_deadline(age, allowed, configured_captcha, clock, monkeypatch):
    result = success(
        clock, challenge_ts=(clock.now() - timedelta(seconds=age)).isoformat()
    )
    monkeypatch.setattr(captcha, "_siteverify", lambda token: result)
    assert check() is allowed


@pytest.mark.parametrize("token", [None, "", "x" * 2049, ["token"]])
def test_invalid_input_never_calls_provider(token, configured_captcha, monkeypatch):
    def reject(_):
        pytest.fail("Provider must not be called")

    monkeypatch.setattr(captcha, "_siteverify", reject)
    assert not check(token)


@pytest.mark.parametrize(
    "error",
    [TimeoutError(), URLError("network"), ValueError("bad JSON"), UnicodeError()],
)
def test_transport_failure_is_closed(error, configured_captcha, monkeypatch):
    def failed(token):
        raise error

    monkeypatch.setattr(captcha, "_siteverify", failed)
    assert not check()


def test_missing_configuration_and_duplicate_form_fields(
    settings, configured_captcha, monkeypatch
):
    settings.TURNSTILE_SECRET_KEY = ""
    assert not check()
    request = RequestFactory().post("/login/", {captcha.TOKEN_FIELD: ["one", "two"]})
    assert not captcha.validate_request(request, "login")


@pytest.mark.parametrize(
    "status,body", [(500, b"{}"), (200, b"invalid"), (200, b"x" * 16385)]
)
def test_bounded_transport_rejects_errors(
    status, body, configured_captcha, monkeypatch
):
    response = MagicMock(status=status)
    response.read.return_value = body
    opener = MagicMock()
    opener.open.return_value.__enter__.return_value = response
    monkeypatch.setattr(captcha, "build_opener", lambda handler: opener)
    assert not check()


def test_fixed_https_transport_and_no_redirect(configured_captcha, monkeypatch, clock):
    import json

    response = MagicMock(status=200)
    response.read.return_value = json.dumps(success(clock)).encode()
    opener = MagicMock()
    opener.open.return_value.__enter__.return_value = response
    monkeypatch.setattr(captcha, "build_opener", lambda handler: opener)
    assert check()
    args, kwargs = opener.open.call_args
    assert (
        args[0].full_url == "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    )
    assert parse_qs(args[0].data.decode())["secret"] == ["private-server-secret"]
    assert kwargs == {"timeout": 5}
    assert response.read.call_args.args == (16385,)
    assert (
        captcha.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other")
        is None
    )


def test_production_config_rejects_missing_keys_test_keys_and_wildcards(monkeypatch):
    monkeypatch.setenv("TURNSTILE_SITE_KEY", "actual-site")
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "actual-secret")
    monkeypatch.setenv("TURNSTILE_ALLOWED_HOSTNAMES", "example.com")
    assert configuration(production=True)[2] == ["example.com"]
    for name, value in [
        ("TURNSTILE_SITE_KEY", ""),
        *[("TURNSTILE_SITE_KEY", key) for key in TEST_SITE_KEYS],
        *[("TURNSTILE_SECRET_KEY", key) for key in TEST_SECRET_KEYS],
        ("TURNSTILE_ALLOWED_HOSTNAMES", "*"),
    ]:
        with monkeypatch.context() as temporary:
            temporary.setenv(name, value)
            with pytest.raises(ImproperlyConfigured) as error:
                configuration(production=True)
            assert "actual-secret" not in str(error.value)


def test_error_reporting_masks_token_and_canary_url(configured_captcha):
    filter = SecurityExceptionReporterFilter()
    request = RequestFactory().post("/login/", {captcha.TOKEN_FIELD: "private-token"})
    assert "private-token" not in str(filter.get_post_parameters(request))
    assert "private" not in filter.cleanse_setting(
        "CANARY_HTTP_TOKEN_URL", "https://private/token"
    )
    assert "private" not in filter.cleanse_setting(
        "TURNSTILE_SECRET_KEY", "private-secret"
    )
