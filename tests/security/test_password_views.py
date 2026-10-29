"""HTTP password changes share policy and invalidate all previous sessions."""

from datetime import timedelta

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client

from apps.security.models import PasswordHistory
from apps.security.selectors import get_security_settings
from apps.security.services import issue_temporary_credential
from apps.security.sessions import CONTEXT_KEY

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("captcha_success")]
OLD = "abcdefghijklmno"
NEW = "completely different new passphrase"


def submit(client, path, old=OLD, new=NEW, confirmation=None):
    return client.post(
        path,
        {
            "old_secret": old,
            "new_secret": new,
            "confirmation": new if confirmation is None else confirmation,
        },
    )


@pytest.mark.parametrize("mode", ["VOLUNTARY", "INITIAL", "RESET", "EXPIRED"])
def test_complete_change_flow(mode, user_factory, admin_factory, clock, client):
    if mode == "INITIAL":
        user = admin_factory(password=OLD)
    else:
        user = user_factory(
            "reader",
            password=OLD,
            credential_mode="PERMANENT",
            password_changed_at=clock.now(),
        )
    secret = OLD
    if mode == "RESET":
        secret = issue_temporary_credential(user.pk).secret
    elif mode == "EXPIRED":
        policy = get_security_settings()
        policy.password_max_age_days = 1
        policy.save()
        clock.advance(timedelta(days=1))
    client.post("/login/", {"login": user.username, "password": secret})
    path = "/password/change/" if mode == "VOLUNTARY" else "/password/required/"
    page = client.get(path)
    assert page.status_code == 200 and "Minimum 14" in page.text
    if mode == "RESET":
        assert "Hasło tymczasowe" in page.text
    result = submit(client, path, secret)
    assert result.url == "/login/?changed=1"
    assert CONTEXT_KEY not in client.session and "_auth_user_id" not in client.session
    assert client.get("/").url == "/login/"
    assert client.post("/login/", {"login": user.username, "password": NEW}).url == "/"
    other = Client()
    assert (
        other.post("/login/", {"login": user.username, "password": secret}).status_code
        == 200
    )
    assert CONTEXT_KEY not in other.session


@pytest.mark.parametrize(
    "failure", ["old", "length", "confirmation", "distance", "history"]
)
def test_rejection_shows_errors_and_preserves_account(
    failure, user_factory, client, clock
):
    user = user_factory(
        "reader",
        password=OLD,
        credential_mode="PERMANENT",
        password_changed_at=clock.now(),
    )
    PasswordHistory.objects.create(
        user=user, password_hash=make_password("retired long passphrase")
    )
    before = (user.password, user.session_version, user.password_changed_at)
    client.post("/login/", {"login": "reader", "password": OLD})
    old, new, confirm = OLD, NEW, NEW
    if failure == "old":
        old = "wrong"
    elif failure == "length":
        new = confirm = "abcdefghijklm"
    elif failure == "confirmation":
        confirm = "mismatch"
    elif failure == "distance":
        new = confirm = "XYZ" + OLD[3:]
    else:
        new = confirm = "retired long passphrase"
    response = submit(client, "/password/change/", old, new, confirm)
    assert response.status_code == 200
    assert response.context["form"].errors
    assert f'value="{new}"' not in response.text
    user.refresh_from_db()
    assert (user.password, user.session_version, user.password_changed_at) == before
    assert user.password_history.count() == 1


def test_four_edits_pass_and_other_sessions_lose_access(user_factory, client):
    user_factory("reader", password=OLD, credential_mode="PERMANENT")
    other = Client()
    for session in (client, other):
        session.post("/login/", {"login": "reader", "password": OLD})
    assert submit(client, "/password/change/", new="WXYZ" + OLD[4:]).status_code == 302
    assert other.get("/").url == "/login/"


def test_disabled_distance_is_described_and_honored(user_factory, client):
    user_factory("reader", password=OLD, credential_mode="PERMANENT")
    policy = get_security_settings()
    policy.levenshtein_enabled = False
    policy.save()
    client.post("/login/", {"login": "reader", "password": OLD})
    assert "co najmniej 4 operacje" not in client.get("/password/change/").text
    assert submit(client, "/password/change/", new="X" + OLD[1:]).status_code == 302
