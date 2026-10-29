"""Administrator policy and private, read-only countdown on the login page."""

from datetime import timedelta

import pytest
from django.test import Client

from apps.security.login_keys import login_identity_key
from apps.security.models import LoginAttemptState
from apps.security.selectors import get_security_settings

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("captcha_success")]
PASSWORD = "previous long passphrase"
SETTINGS_URL = "/management/security/"


def values(limit):
    return {
        "levenshtein_enabled": "on",
        "password_max_age_days": "0",
        "idle_timeout_minutes": "15",
        "login_failure_limit": limit,
    }


@pytest.fixture
def administrator(admin_factory, client):
    user = admin_factory(password=PASSWORD, credential_mode="PERMANENT")
    assert (
        client.post("/login/", {"login": "ADMIN", "password": PASSWORD}).status_code
        == 302
    )
    return user


def test_administrator_can_update_threshold_without_changing_session_limit(
    administrator, client
):
    page = client.get(SETTINGS_URL)
    assert 'name="login_failure_limit"' in page.text
    assert "osobna zasada od bezczynności" in page.text
    assert client.post(SETTINGS_URL, values("2")).status_code == 302
    policy = get_security_settings()
    assert policy.login_failure_limit == 2
    assert policy.idle_timeout_minutes == 15
    csrf = Client(enforce_csrf_checks=True)
    csrf.cookies = client.cookies.copy()
    assert csrf.post(SETTINGS_URL, values("1")).status_code == 403
    assert get_security_settings().login_failure_limit == 2


@pytest.mark.parametrize("limit", ["0", "-1", "1.5", "abc", "", None])
def test_invalid_threshold_preserves_all_settings(administrator, client, limit):
    before = get_security_settings()
    response = client.post(SETTINGS_URL, values(limit) if limit is not None else {})
    assert response.status_code == 200
    assert "login_failure_limit" in response.context["form"].errors
    after = get_security_settings()
    assert (after.login_failure_limit, after.updated_at) == (
        before.login_failure_limit,
        before.updated_at,
    )


@pytest.mark.parametrize("role", ["MANAGER", "EDITOR", "EMPLOYEE", "READER"])
def test_other_roles_cannot_read_or_update_threshold(role, user_factory, client):
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT", role=role)
    client.post("/login/", {"login": "reader", "password": PASSWORD})
    assert client.get(SETTINGS_URL).status_code == 403
    assert client.post(SETTINGS_URL, values("1")).status_code == 403
    assert get_security_settings().login_failure_limit == 5


@pytest.mark.parametrize("existing", [False, True])
def test_countdown_for_known_and_unknown_logins_is_private_and_does_not_extend(
    existing, user_factory, client, clock
):
    secret = "must-not-be-displayed-secret"
    if existing:
        user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    policy = get_security_settings()
    policy.login_failure_limit = 1
    policy.save()
    data = {"login": "reader", "password": secret}
    response = client.post("/login/", data)
    assert response.context["login_block_seconds"] == 900
    assert 'data-remaining-seconds="900"' in response.text
    assert ">15:00</span>" in response.text
    assert "js/login-lock.js" in response.text
    assert secret not in response.text
    assert "no-store" in response.headers["Cache-Control"]
    assert "Location" not in response.headers
    assert "sessionid" not in response.cookies
    state = LoginAttemptState.objects.get(identity_key=login_identity_key("reader"))
    original = (
        state.failure_count,
        state.blocked_until,
        state.version,
        state.updated_at,
    )
    clock.advance(timedelta(seconds=20, microseconds=1))
    response = client.post("/login/", data)
    assert response.context["login_block_seconds"] == 880  # rounded upward
    assert response.context["login_block_time"] == "14:40"
    state.refresh_from_db()
    assert (
        state.failure_count,
        state.blocked_until,
        state.version,
        state.updated_at,
    ) == original
    clock.set(state.blocked_until)
    # A malformed request reports field errors, not an expired block.
    response = client.post("/login/", {"login": "reader"})
    assert "login_block_seconds" not in response.context
    assert "js/login-lock.js" not in response.text


def test_plain_get_never_creates_counter_or_discloses_a_login(client):
    response = client.get("/login/")
    assert response.status_code == 200
    assert "js/login-lock.js" not in response.text
    assert not LoginAttemptState.objects.exists()
