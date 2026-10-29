"""Controlled clock tests for exact limits and policy changes in live sessions."""

from datetime import timedelta

import pytest
from django.http import HttpResponse
from django.test import Client, override_settings
from django.urls import include, path

from apps.accounts.views import dashboard
from apps.security.middleware import passive_view
from apps.security.selectors import get_security_settings
from apps.security.services import issue_temporary_credential
from apps.security.sessions import CONTEXT_KEY, access_required

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("captcha_success")]
PASSWORD = "previous long passphrase"


@passive_view
@access_required("full")
def poll(request):
    return HttpResponse("ok")


urlpatterns = [
    path("", dashboard, name="home"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.security.urls")),
    path("poll/", poll),
    path("static/probe.css", lambda request: HttpResponse("body {}")),
]


@pytest.fixture
def logged_in(user_factory, client, clock):
    user = user_factory(
        "reader",
        password=PASSWORD,
        credential_mode="PERMANENT",
        password_changed_at=clock.now(),
    )
    client.post("/login/", {"login": "reader", "password": PASSWORD})
    return user


@pytest.mark.parametrize("microseconds, active", [(-1, True), (0, False), (1, False)])
def test_full_idle_boundary(logged_in, client, clock, microseconds, active):
    clock.advance(timedelta(minutes=15, microseconds=microseconds))
    response = client.get("/")
    assert response.status_code == (200 if active else 302)
    if not active:
        assert response.url == "/login/"
        assert CONTEXT_KEY not in client.session
        assert client.get("/").url == "/login/"


def test_activity_renews_but_policy_shortening_applies_immediately(
    logged_in, client, clock
):
    clock.advance(timedelta(minutes=14))
    assert client.get("/").status_code == 200
    clock.advance(timedelta(minutes=2))
    assert client.get("/").status_code == 200
    clock.advance(timedelta(minutes=1))
    policy = get_security_settings()
    policy.idle_timeout_minutes = 1
    policy.save()
    assert client.get("/").url == "/login/"


@pytest.mark.parametrize("path", ["/poll/", "/static/probe.css"])
@override_settings(ROOT_URLCONF=__name__)
def test_passive_requests_do_not_extend_activity(logged_in, client, clock, path):
    original = client.session[CONTEXT_KEY]["last_activity"]
    clock.advance(timedelta(minutes=14))
    assert client.get(path).status_code == 200
    assert client.session[CONTEXT_KEY]["last_activity"] == original
    clock.advance(timedelta(minutes=1))
    assert client.get("/").url == "/login/"


def test_expiry_policy_downgrades_existing_full_context(logged_in, client, clock):
    # Idle timeout is independently enlarged, preserving the initial activity.
    policy = get_security_settings()
    policy.idle_timeout_minutes = 3000
    policy.save()
    clock.advance(timedelta(days=1))
    assert client.get("/").status_code == 200  # default 0 disables password expiry
    key = client.session.session_key
    policy.password_max_age_days = 1
    policy.save()
    response = client.get("/")
    assert response.url == "/password/required/"
    assert "_auth_user_id" not in client.session
    assert client.session.session_key != key
    assert client.session[CONTEXT_KEY]["reason"] == "EXPIRED"
    assert client.get("/password/required/").status_code == 200


@pytest.mark.parametrize("boundary", ["idle", "credential"])
def test_temporary_context_uses_earlier_deadline(boundary, user_factory, client, clock):
    user = user_factory("reader")
    issued = issue_temporary_credential(user.pk)
    if boundary == "credential":
        clock.set(issued.expires_at - timedelta(minutes=1))
    client.post("/login/", {"login": "reader", "password": issued.secret})
    clock.advance(timedelta(minutes=15 if boundary == "idle" else 1))
    assert client.get("/password/required/").url == "/login/"
    assert CONTEXT_KEY not in client.session
    # Consumed secrets cannot restore a lost limited context.
    assert (
        client.post(
            "/login/", {"login": "reader", "password": issued.secret}
        ).status_code
        == 200
    )
    assert CONTEXT_KEY not in client.session


@pytest.mark.parametrize("change", ["blocked", "deleted", "version"])
def test_account_changes_revoke_existing_context(logged_in, client, clock, change):
    if change == "version":
        logged_in.session_version += 1
    else:
        logged_in.is_active = False
        if change == "deleted":
            logged_in.deleted_at = clock.now()
    logged_in.save()
    assert client.get("/").url == "/login/"
    assert CONTEXT_KEY not in client.session


def test_old_cookie_cannot_restore_expired_session(logged_in, client, clock):
    cookie = client.cookies["sessionid"].value
    clock.advance(timedelta(minutes=15))
    client.get("/")
    other = Client()
    other.cookies["sessionid"] = cookie
    assert other.get("/").url == "/login/"


def test_invalid_activity_timestamp_fails_closed(logged_in, client):
    session = client.session
    session[CONTEXT_KEY] = {**session[CONTEXT_KEY], "last_activity": "invalid"}
    session.save()
    assert client.get("/").url == "/login/"


@pytest.mark.parametrize("microseconds, expired", [(-1, False), (0, True), (1, True)])
def test_password_expiry_boundary_in_existing_session(
    logged_in, client, clock, microseconds, expired
):
    policy = get_security_settings()
    policy.password_max_age_days = 1
    policy.idle_timeout_minutes = 3000
    policy.save()
    clock.advance(timedelta(days=1, microseconds=microseconds))
    response = client.get("/")
    if expired:
        assert response.url == "/password/required/"
        assert "_auth_user_id" not in client.session
    else:
        assert response.status_code == 200


def test_activity_never_extends_original_temporary_deadline(
    user_factory, client, clock
):
    user = user_factory("reader")
    issued = issue_temporary_credential(user.pk)
    clock.set(issued.expires_at - timedelta(minutes=1))
    client.post("/login/", {"login": "reader", "password": issued.secret})
    clock.advance(timedelta(seconds=30))
    assert client.get("/password/required/").status_code == 200
    assert client.session[CONTEXT_KEY]["expires_at"] == issued.expires_at.isoformat()
    clock.advance(timedelta(seconds=30))
    assert client.get("/password/required/").url == "/login/"
