"""Uniform login errors and explicit credential modes without fallback access."""

from datetime import timedelta

import pytest
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password

from apps.accounts import backends
from apps.accounts.backends import LOGIN_ERROR, authenticate_login
from apps.accounts.forms import LoginForm
from apps.security.models import TemporaryCredential
from apps.security.selectors import get_security_settings
from apps.security.services import issue_temporary_credential

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("captcha_success")]
PASSWORD = "  exact previous passphrase  "


def test_login_uses_normalized_login_and_exact_password(user_factory, client, settings):
    user = user_factory("Żaneta", password=PASSWORD, credential_mode="PERMANENT")
    assert authenticate_login(" ŻANETA ", PASSWORD).user_id == user.pk
    assert authenticate_login("żaneta", PASSWORD.strip()) is None
    assert authenticate(username="Żaneta", password=PASSWORD).pk == user.pk
    assert settings.AUTHENTICATION_BACKENDS == [backends.BACKEND_PATH]
    response = client.get("/login/")
    assert 'type="password"' in response.text
    assert response.status_code == 200


@pytest.mark.parametrize(
    "state",
    [
        "missing",
        "wrong",
        "blocked",
        "deleted",
        "expired_temp",
        "consumed",
        "revoked",
        "reset_old",
    ],
)
def test_refusals_share_one_message(state, user_factory, clock, client):
    user = user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    login, password = "reader", PASSWORD
    if state == "missing":
        login = "absent"
    elif state == "wrong":
        password = "wrong"
    elif state in ("blocked", "deleted"):
        user.is_active = False
        user.deleted_at = clock.now() if state == "deleted" else None
        user.save()
    else:
        issued = issue_temporary_credential(user.pk)
        password = PASSWORD if state == "reset_old" else issued.secret
        if state == "expired_temp":
            clock.set(issued.expires_at)
        elif state in ("consumed", "revoked"):
            field = "consumed_at" if state == "consumed" else "revoked_at"
            TemporaryCredential.objects.filter(pk=issued.credential_id).update(
                **{field: clock.now()}
            )
    form = LoginForm({"login": login, "password": password})
    # Field validation is separate from the atomic login/limit service.
    assert form.is_valid()
    assert authenticate(username=login, password=password) is None
    response = client.post("/login/", {"login": login, "password": password})
    assert LOGIN_ERROR in response.text
    assert "_auth_user_id" not in client.session


def test_initial_and_expired_and_temporary_are_restricted(
    admin_factory, user_factory, clock
):
    admin_factory(password=PASSWORD)
    assert authenticate_login("admin", PASSWORD).reason == "INITIAL"
    assert authenticate(username="ADMIN", password=PASSWORD) is None
    user = user_factory(
        "reader",
        password=PASSWORD,
        credential_mode="PERMANENT",
        password_changed_at=clock.now(),
    )
    policy = get_security_settings()
    policy.password_max_age_days = 1
    policy.save()
    clock.advance(timedelta(days=1))
    assert authenticate_login("reader", PASSWORD).reason == "EXPIRED"
    assert authenticate(username="reader", password=PASSWORD) is None
    issued = issue_temporary_credential(user.pk)
    result = authenticate_login("reader", issued.secret)
    assert result.reason == "RESET" and result.credential_id == issued.credential_id
    assert authenticate(username="reader", password=issued.secret) is None


def test_missing_login_runs_costly_dummy_hash(monkeypatch):
    calls = []
    original = make_password

    def dummy(value):
        calls.append(True)
        return original(value)

    monkeypatch.setattr(backends, "make_password", dummy)
    assert authenticate_login("absent", PASSWORD) is None
    assert calls == [True]
