"""CSRF, server invalidation, cache protection and redacted error reports."""

import json
import sys
from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.test import Client, RequestFactory, override_settings
from django.views.debug import ExceptionReporter, get_default_exception_reporter_filter

from apps.security.reporting import SecurityExceptionReporterFilter
from apps.security.selectors import get_security_settings
from apps.security.services import issue_temporary_credential
from apps.security.sessions import CONTEXT_KEY

pytestmark = pytest.mark.django_db
PASSWORD = "previous long passphrase"


def csrf(client, path):
    response = client.get(path)
    assert response.status_code == 200
    return client.cookies["csrftoken"].value


@pytest.mark.parametrize("limited", [False, True])
def test_logout_requires_post_and_csrf_and_invalidates_server_session(
    limited, user_factory
):
    user = user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    secret = issue_temporary_credential(user.pk).secret if limited else PASSWORD
    client = Client(enforce_csrf_checks=True)
    token = csrf(client, "/login/")
    login_token = token
    assert (
        client.post("/login/", {"login": "reader", "password": secret}).status_code
        == 403
    )
    client.post(
        "/login/", {"login": "reader", "password": secret, "csrfmiddlewaretoken": token}
    )
    path = "/password/required/" if limited else "/"
    token = csrf(client, path)  # login rotates CSRF token
    assert token != login_token
    key = client.session.session_key
    assert client.get("/logout/").status_code == 405
    assert CONTEXT_KEY in client.session
    assert client.post("/logout/").status_code == 403
    assert CONTEXT_KEY in client.session
    response = client.post("/logout/", {"csrfmiddlewaretoken": token})
    assert response.url == "/login/?logged_out=1"
    assert client.cookies["csrftoken"].value != token
    assert not Session.objects.filter(session_key=key).exists()
    other = Client()
    other.cookies["sessionid"] = key
    assert other.get("/").url == "/login/"


@pytest.mark.parametrize("limited", [False, True])
def test_password_change_csrf_cannot_be_bypassed(limited, user_factory):
    user = user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    secret = issue_temporary_credential(user.pk).secret if limited else PASSWORD
    client = Client(enforce_csrf_checks=True)
    token = csrf(client, "/login/")
    client.post(
        "/login/", {"login": "reader", "password": secret, "csrfmiddlewaretoken": token}
    )
    path = "/password/required/" if limited else "/password/change/"
    response = client.post(
        path,
        {
            "old_secret": secret,
            "new_secret": "new completely different phrase",
            "confirmation": "new completely different phrase",
        },
    )
    assert response.status_code == 403
    assert "no-store" in response.headers["Cache-Control"]
    user.refresh_from_db()
    assert user.password_changed_at is None


def test_protected_and_secret_views_are_not_cached(user_factory, client):
    assert "no-store" in client.get("/login/").headers["Cache-Control"]
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    client.post("/login/", {"login": "reader", "password": PASSWORD})
    for path in ("/", "/password/change/", "/password/required/", "/logout/"):
        response = client.get(path)
        assert "no-store" in response.headers["Cache-Control"]
        assert "private" in response.headers["Cache-Control"]
    cookie = client.cookies["sessionid"]
    assert cookie["httponly"] and cookie["samesite"] == "Lax"


@override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
def test_https_sets_secure_cookies(user_factory):
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    client = Client()
    client.get("/login/", secure=True)
    client.post("/login/", {"login": "reader", "password": PASSWORD}, secure=True)
    assert client.cookies["sessionid"]["secure"]
    assert client.cookies["csrftoken"]["secure"]


@override_settings(DEBUG=True)
def test_error_filter_redacts_post_and_cookies_even_in_local_debug(settings):
    request = RequestFactory().post(
        "/login/", {"password": "sensitive-input", "new_secret": "sensitive-new-input"}
    )
    request.COOKIES[settings.SESSION_COOKIE_NAME] = "sensitive-session-cookie"
    request.COOKIES[settings.CSRF_COOKIE_NAME] = "sensitive-csrf-cookie"
    reporter_filter = get_default_exception_reporter_filter()
    assert isinstance(reporter_filter, SecurityExceptionReporterFilter)
    assert "sensitive" not in str(reporter_filter.get_post_parameters(request))
    assert "sensitive" not in str(reporter_filter.get_safe_cookies(request))
    try:
        raise RuntimeError("simulated error")
    except RuntimeError:
        report = ExceptionReporter(request, *sys.exc_info()).get_traceback_text()
    for value in (
        "sensitive-input",
        "sensitive-new-input",
        "sensitive-session-cookie",
        "sensitive-csrf-cookie",
    ):
        assert value not in report


def test_credentials_do_not_appear_in_sessions_logs_or_redirects(
    user_factory, client, caplog
):
    user = user_factory("reader")
    issued = issue_temporary_credential(user.pk)
    response = client.post("/login/", {"login": "reader", "password": issued.secret})
    serialized = json.dumps(dict(client.session))
    key = client.session.session_key
    assert issued.secret not in serialized + response.url + caplog.text
    assert key not in caplog.text
    changed = client.post(
        "/password/required/",
        {
            "old_secret": issued.secret,
            "new_secret": "new completely different phrase",
            "confirmation": "new completely different phrase",
        },
    )
    assert changed.status_code == 302
    assert (
        "new completely different phrase"
        not in changed.url + caplog.text + json.dumps(dict(client.session))
    )


def test_expired_context_can_change_password_after_expiry_is_disabled(
    user_factory, client, clock
):
    user_factory(
        "reader",
        password=PASSWORD,
        credential_mode="PERMANENT",
        password_changed_at=clock.now(),
    )
    policy = get_security_settings()
    policy.password_max_age_days = 1
    policy.save()
    clock.advance(timedelta(days=1))
    assert (
        client.post("/login/", {"login": "reader", "password": PASSWORD}).url
        == "/password/required/"
    )
    policy.password_max_age_days = 0
    policy.save()
    assert client.get("/").url == "/password/required/"
    response = client.post(
        "/password/required/",
        {
            "old_secret": PASSWORD,
            "new_secret": "new completely different phrase",
            "confirmation": "new completely different phrase",
        },
    )
    assert response.url == "/login/?changed=1"
