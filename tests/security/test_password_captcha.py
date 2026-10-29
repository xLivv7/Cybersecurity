"""CAPTCHA must precede password mutation in every full/limited context."""

from datetime import timedelta
from unittest.mock import Mock

import pytest
from django.utils import timezone

from apps.security import captcha, views
from apps.security.models import PasswordHistory, TemporaryCredential
from apps.security.selectors import get_security_settings
from apps.security.services import issue_temporary_credential
from apps.security.sessions import CONTEXT_KEY

pytestmark = pytest.mark.django_db
OLD = "previous long passphrase"
NEW = "a completely unrelated secure phrase"


@pytest.fixture
def scenario(
    request, settings, user_factory, admin_factory, client, clock, monkeypatch
):
    mode = request.param
    settings.TURNSTILE_SITE_KEY = "public-site"
    settings.TURNSTILE_SECRET_KEY = "private-secret"
    settings.TURNSTILE_ALLOWED_HOSTNAMES = ["testserver"]
    user = (
        admin_factory(password=OLD)
        if mode == "INITIAL"
        else user_factory(
            "reader",
            password=OLD,
            credential_mode="PERMANENT",
            password_changed_at=clock.now(),
        )
    )
    secret = OLD
    if mode == "RESET":
        secret = issue_temporary_credential(user.pk).secret
    elif mode == "EXPIRED":
        policy = get_security_settings()
        policy.password_max_age_days = 1
        policy.save()
        clock.advance(timedelta(days=1))
    action = "password_change" if mode == "VOLUNTARY" else "password_required"

    def provider(token):
        return {
            "success": token in ("login-token", "change-token"),
            "hostname": "testserver",
            "action": "login" if token == "login-token" else action,
            "challenge_ts": timezone.now().isoformat(),
        }

    monkeypatch.setattr(captcha, "_siteverify", provider)
    assert (
        client.post(
            "/login/",
            {
                "login": user.username,
                "password": secret,
                captcha.TOKEN_FIELD: "login-token",
            },
        ).status_code
        == 302
    )
    path = "/password/change/" if mode == "VOLUNTARY" else "/password/required/"
    return user, secret, path, action


def snapshot(user):
    return (
        type(user).objects.values().get(pk=user.pk),
        list(PasswordHistory.objects.filter(user=user).values()),
        list(TemporaryCredential.objects.filter(user=user).values()),
    )


@pytest.mark.parametrize(
    "scenario", ["VOLUNTARY", "INITIAL", "RESET", "EXPIRED"], indirect=True
)
@pytest.mark.parametrize("token", [None, "invalid", "login-token"])
def test_rejected_token_cannot_mutate_credentials(scenario, token, client, monkeypatch):
    user, secret, path, action = scenario
    before = snapshot(user)
    version = client.session[CONTEXT_KEY]["version"]
    save = Mock(side_effect=AssertionError("Password service must not be called"))
    monkeypatch.setattr(views.PasswordChangeForm, "save", save)
    data = {"old_secret": secret, "new_secret": NEW, "confirmation": NEW}
    if token is not None:
        data[captcha.TOKEN_FIELD] = token
    response = client.post(path, data)
    assert response.status_code == 200
    assert captcha.CAPTCHA_ERROR in response.text
    assert f'data-action="{action}"' in response.text
    assert snapshot(user) == before
    assert client.session[CONTEXT_KEY]["version"] == version
    assert secret not in response.text and NEW not in response.text
    save.assert_not_called()


@pytest.mark.parametrize(
    "scenario", ["VOLUNTARY", "INITIAL", "RESET", "EXPIRED"], indirect=True
)
def test_valid_captcha_preserves_required_relogin(scenario, client):
    user, secret, path, action = scenario
    version = client.session[CONTEXT_KEY]["version"]
    response = client.post(
        path,
        {
            "old_secret": secret,
            "new_secret": NEW,
            "confirmation": NEW,
            captcha.TOKEN_FIELD: "change-token",
        },
    )
    assert response.url == "/login/?changed=1"
    user.refresh_from_db()
    assert user.check_password(NEW)
    assert user.session_version == version + 1
    assert user.credential_mode == "PERMANENT"
    assert CONTEXT_KEY not in client.session
