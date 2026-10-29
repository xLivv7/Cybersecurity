"""Replay and concurrent HTTP requests must not reach credential operations twice."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.db import connections
from django.test import Client
from django.utils import timezone

from apps.security import captcha, login_limits, views
from apps.security.models import CaptchaRedemption, LoginAttemptState
from apps.security.sessions import CONTEXT_KEY

pytestmark = pytest.mark.django_db
PASSWORD = "previous long passphrase"
NEW = "a completely unrelated secure phrase"


@pytest.fixture
def config(settings):
    settings.TURNSTILE_SITE_KEY = "configured-site"
    settings.TURNSTILE_SECRET_KEY = "private-secret"
    settings.TURNSTILE_ALLOWED_HOSTNAMES = ["testserver"]


def valid(action="login", **changes):
    return {
        "success": True,
        "hostname": "testserver",
        "action": action,
        "challenge_ts": timezone.now().isoformat(),
        **changes,
    }


@pytest.mark.parametrize(
    "age,allowed", [(299.999999, True), (300, False), (300.000001, False)]
)
def test_deadline_through_http(
    age, allowed, config, user_factory, clock, monkeypatch, client
):
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    monkeypatch.setattr(
        captcha,
        "_siteverify",
        lambda token: valid(
            challenge_ts=(clock.now() - timedelta(seconds=age)).isoformat()
        ),
    )
    response = client.post(
        "/login/",
        {
            "login": "reader",
            "password": PASSWORD,
            captcha.TOKEN_FIELD: "boundary-token",
        },
    )
    assert response.status_code == (302 if allowed else 200)
    assert (CONTEXT_KEY in client.session) is allowed
    assert LoginAttemptState.objects.count() == int(allowed)


def test_duplicate_fields_and_transport_error_do_not_check_password(
    config, monkeypatch, client
):
    provider = Mock(side_effect=TimeoutError())
    verify = Mock(side_effect=AssertionError("Must not check password"))
    monkeypatch.setattr(captcha, "_siteverify", provider)
    monkeypatch.setattr(login_limits, "authenticate_login", verify)
    data = {
        "login": "reader",
        "password": PASSWORD,
        captcha.TOKEN_FIELD: ["one", "two"],
    }
    assert captcha.CAPTCHA_ERROR in client.post("/login/", data).text
    provider.assert_not_called()
    data[captcha.TOKEN_FIELD] = "network-timeout"
    assert captcha.CAPTCHA_ERROR in client.post("/login/", data).text
    assert provider.call_count == 1
    verify.assert_not_called()
    assert not LoginAttemptState.objects.exists()


def test_wrong_action_and_replay_across_password_form(
    config, user_factory, client, monkeypatch
):
    user = user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    monkeypatch.setattr(captcha, "_siteverify", lambda token: valid())
    assert (
        client.post(
            "/login/",
            {
                "login": "reader",
                "password": PASSWORD,
                captcha.TOKEN_FIELD: "login-token",
            },
        ).status_code
        == 302
    )
    before = type(user).objects.values().get(pk=user.pk)
    for token in ["login-token", "fresh-with-wrong-action"]:
        response = client.post(
            "/password/change/",
            {
                "old_secret": PASSWORD,
                "new_secret": NEW,
                "confirmation": NEW,
                captcha.TOKEN_FIELD: token,
            },
        )
        assert captcha.CAPTCHA_ERROR in response.text
        assert type(user).objects.values().get(pk=user.pk) == before
    assert CaptchaRedemption.objects.count() == 1


def test_password_validation_error_requires_fresh_challenge(
    config, user_factory, client, monkeypatch
):
    user = user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    monkeypatch.setattr(
        captcha,
        "_siteverify",
        lambda token: valid("login" if token == "login" else "password_change"),
    )
    client.post(
        "/login/",
        {"login": "reader", "password": PASSWORD, captcha.TOKEN_FIELD: "login"},
    )
    data = {
        "old_secret": PASSWORD,
        "new_secret": NEW,
        "confirmation": "mismatch",
        captcha.TOKEN_FIELD: "first-change",
    }
    response = client.post("/password/change/", data)
    assert response.status_code == 200 and response.context["form"].errors
    assert 'data-action="password_change"' in response.text
    assert "first-change" not in response.text and NEW not in response.text
    original = views.PasswordChangeForm.save
    save = Mock(side_effect=AssertionError("Replay must not call password service"))
    monkeypatch.setattr(views.PasswordChangeForm, "save", save)
    data["confirmation"] = NEW
    assert captcha.CAPTCHA_ERROR in client.post("/password/change/", data).text
    save.assert_not_called()
    monkeypatch.setattr(views.PasswordChangeForm, "save", original)
    data[captcha.TOKEN_FIELD] = "fresh-change"
    assert client.post("/password/change/", data).url == "/login/?changed=1"
    user.refresh_from_db()
    assert user.check_password(NEW)


def test_malformed_unicode_and_nested_json_fail_closed(config, monkeypatch):
    assert not captcha.validate_token("\ud800", action="login", hostname="testserver")

    def malformed(token):
        raise RecursionError()

    monkeypatch.setattr(captcha, "_siteverify", malformed)
    assert not captcha.validate_token("nested", action="login", hostname="testserver")


@pytest.mark.django_db(transaction=True)
def test_two_http_requests_cannot_redeem_same_token(file_database, config, monkeypatch):
    get_user_model().objects.create_user(
        "reader", password=PASSWORD, credential_mode="PERMANENT"
    )
    barrier = Barrier(2)

    def provider(token):
        result = valid()
        barrier.wait(timeout=15)
        return result

    monkeypatch.setattr(captcha, "_siteverify", provider)

    def submit():
        try:
            response = Client().post(
                "/login/",
                {
                    "login": "reader",
                    "password": PASSWORD,
                    captcha.TOKEN_FIELD: "same-token",
                },
            )
            return CONTEXT_KEY in response.wsgi_request.session
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: submit(), range(2)))
    assert sorted(results) == [False, True]
    assert CaptchaRedemption.objects.count() == 1
    assert LoginAttemptState.objects.get().version == 1
