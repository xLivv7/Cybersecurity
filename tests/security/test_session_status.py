"""Passive status checks must reflect server deadlines without extending them."""

from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.test import Client

from apps.security.selectors import get_security_settings
from apps.security.services import issue_temporary_credential
from apps.security.sessions import CONTEXT_KEY

pytestmark = pytest.mark.django_db
PASSWORD = "previous long passphrase"
URL = "/session/status/"


@pytest.fixture
def logged_in(admin_factory, client, clock):
    user = admin_factory(
        password=PASSWORD,
        credential_mode="PERMANENT",
        password_changed_at=clock.now(),
    )
    assert (
        client.post("/login/", {"login": user.username, "password": PASSWORD}).url
        == "/"
    )
    return user


def test_polling_never_renews_and_expires_at_exact_boundary(logged_in, client, clock):
    original = client.session[CONTEXT_KEY]["last_activity"]
    key = client.session.session_key
    for _ in range(29):
        clock.advance(timedelta(seconds=30))
        response = client.get(URL)
        assert response.json() == {
            "active": True,
            "scope": "full",
            "remaining_seconds": 900 - (_ + 1) * 30,
        }
        assert client.session[CONTEXT_KEY]["last_activity"] == original
        assert "no-store" in response.headers["Cache-Control"]
    clock.advance(timedelta(seconds=30))
    assert client.get(URL).json() == {"active": False}
    assert not Session.objects.filter(session_key=key).exists()
    assert client.get("/").url == "/login/"


def test_another_tab_activity_is_respected(logged_in, client, clock):
    other_tab = Client()
    other_tab.cookies = client.cookies.copy()
    clock.advance(timedelta(minutes=14))
    assert other_tab.get("/").status_code == 200
    clock.advance(timedelta(minutes=1))
    assert client.get(URL).json()["remaining_seconds"] == 840


def test_shortened_policy_applies_to_passive_status(logged_in, client, clock):
    clock.advance(timedelta(minutes=2))
    policy = get_security_settings()
    policy.idle_timeout_minutes = 1
    policy.save()
    assert client.get(URL).json() == {"active": False}


def test_password_expiry_returns_limited_scope(logged_in, client, clock):
    policy = get_security_settings()
    policy.idle_timeout_minutes = 3000
    policy.password_max_age_days = 1
    policy.save()
    clock.advance(timedelta(days=1))
    assert client.get(URL).json() == {
        "active": True,
        "scope": "limited",
        "remaining_seconds": 93600,
    }
    assert "_auth_user_id" not in client.session


@pytest.mark.parametrize("mode", ["INITIAL", "RESET"])
def test_limited_context_status_and_original_deadline(
    mode, user_factory, admin_factory, client, clock
):
    user = (
        admin_factory(password=PASSWORD)
        if mode == "INITIAL"
        else user_factory("reader", password=PASSWORD)
    )
    secret = PASSWORD
    if mode == "RESET":
        issued = issue_temporary_credential(user.pk)
        secret = issued.secret
        clock.set(issued.expires_at - timedelta(seconds=30))
    client.post("/login/", {"login": user.username, "password": secret})
    original = client.session[CONTEXT_KEY]["last_activity"]
    expected = 30 if mode == "RESET" else 900
    assert client.get(URL).json() == {
        "active": True,
        "scope": "limited",
        "remaining_seconds": expected,
    }
    assert client.session[CONTEXT_KEY]["last_activity"] == original
    clock.advance(timedelta(seconds=expected))
    assert client.get(URL).json() == {"active": False}


def test_anonymous_status_is_private_and_creates_no_session(client):
    response = client.get(URL)
    assert response.json() == {"active": False}
    assert "no-store" in response.headers["Cache-Control"]
    assert "sessionid" not in response.cookies
    assert client.post(URL).status_code == 405
    assert b"js/session.js" not in client.get("/login/").content


def test_protected_page_loads_timer_and_expiry_message(logged_in, client):
    content = client.get("/").content
    assert b"js/session.js" in content
    assert b'data-status-url="/session/status/"' in content
    client.post("/logout/")
    assert "Sesja wygasła" in client.get("/login/?expired=1").content.decode()


def test_invalid_timestamp_returns_inactive_json(logged_in, client):
    session = client.session
    session[CONTEXT_KEY] = {**session[CONTEXT_KEY], "last_activity": "invalid"}
    session.save()
    assert client.get(URL).json() == {"active": False}
