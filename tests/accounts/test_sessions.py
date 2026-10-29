"""A restricted login never sets Django's authenticated-user session key."""

import json
from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import Client

from apps.security.models import TemporaryCredential
from apps.security.selectors import get_security_settings
from apps.security.services import issue_temporary_credential
from apps.security.sessions import CONTEXT_KEY

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("captcha_success")]
PASSWORD = "previous long passphrase"


def test_full_login_rotates_key_and_protects_dashboard(user_factory, client):
    user = user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    assert client.get("/").url == "/login/"
    session = client.session
    session["untrusted"] = "old"
    session.save()
    old_key = session.session_key
    response = client.post("/login/", {"login": "reader", "password": PASSWORD})
    assert response.url == "/"
    assert client.session.session_key != old_key
    assert "untrusted" not in client.session
    assert client.session["_auth_user_id"] == str(user.pk)
    assert client.get("/").status_code == 200


@pytest.mark.parametrize("mode", ["INITIAL", "RESET", "EXPIRED"])
def test_restricted_context_has_no_full_access(
    mode, admin_factory, user_factory, client, clock
):
    credential_id = None
    if mode == "INITIAL":
        user = admin_factory(password=PASSWORD)
        password = PASSWORD
    else:
        user = user_factory(
            "reader",
            password=PASSWORD,
            credential_mode="PERMANENT",
            password_changed_at=clock.now(),
        )
        password = PASSWORD
        if mode == "RESET":
            issued = issue_temporary_credential(user.pk)
            password, credential_id = issued.secret, issued.credential_id
        else:
            policy = get_security_settings()
            policy.password_max_age_days = 1
            policy.save()
            clock.advance(timedelta(days=1))
    response = client.post("/login/", {"login": user.username, "password": password})
    assert response.url == "/password/required/"
    assert "_auth_user_id" not in client.session
    context = client.session[CONTEXT_KEY]
    assert context["reason"] == mode
    assert context["credential_id"] == credential_id
    assert password not in json.dumps(dict(client.session))
    assert client.get("/").url == "/password/required/"
    required = client.get("/password/required/")
    assert required.status_code == 200
    assert (
        isinstance(required.wsgi_request.user, AnonymousUser)
        or required.wsgi_request.user.is_anonymous
    )
    assert client.get("/management/users/").url == "/password/required/"
    if credential_id:
        assert TemporaryCredential.objects.get(pk=credential_id).consumed_at is not None
        other = Client()
        assert (
            other.post(
                "/login/", {"login": user.username, "password": password}
            ).status_code
            == 200
        )
        assert CONTEXT_KEY not in other.session


def test_reset_invalidates_full_context_on_next_protected_request(user_factory, client):
    user = user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    client.post("/login/", {"login": "reader", "password": PASSWORD})
    issue_temporary_credential(user.pk)
    assert client.get("/").url == "/login/"
    assert CONTEXT_KEY not in client.session
