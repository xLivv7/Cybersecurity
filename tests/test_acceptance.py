"""Cross-module acceptance gaps: CSRF, redirects, reset history and live access."""

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client

from apps.documents.models import Document
from apps.security.models import PasswordHistory
from apps.security.sessions import CONTEXT_KEY

pytestmark = pytest.mark.django_db
PASSWORD = "previous long passphrase"


@pytest.mark.parametrize(
    "next_url, expected",
    [
        ("/documents/", "/documents/"),
        ("https://example.org/", "/"),
        ("//example.org/", "/"),
        ("/\\example.org/", "/"),
    ],
)
def test_login_return_address_is_local(next_url, expected, user_factory, client):
    from urllib.parse import urlencode

    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    response = client.post(
        "/login/?" + urlencode({"next": next_url}),
        {"login": "reader", "password": PASSWORD},
    )
    assert response.url == expected


def test_document_csrf_author_and_state_are_protected(user_factory):
    user = user_factory(
        "manager", password=PASSWORD, role="MANAGER", credential_mode="PERMANENT"
    )
    document = Document.objects.create(author=user, title="Before", body="Text")
    client = Client(enforce_csrf_checks=True)
    client.get("/login/")
    client.post(
        "/login/",
        {
            "login": "manager",
            "password": PASSWORD,
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        },
    )
    for url, payload in [
        ("/documents/new/", {"title": "Injected", "body": "Injected"}),
        (f"/documents/{document.pk}/edit/", {"title": "Injected", "body": "Injected"}),
        (f"/documents/{document.pk}/publish/", {}),
        (f"/documents/{document.pk}/withdraw/", {}),
    ]:
        assert client.post(url, payload).status_code == 403
    document.refresh_from_db()
    assert document.title == "Before" and document.status == "DRAFT"
    assert Document.objects.count() == 1


def test_admin_reset_preserves_history_and_revokes_real_sessions(
    admin_factory, user_factory, client, caplog
):
    admin_factory(password=PASSWORD, credential_mode="PERMANENT")
    user = user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    historical = "historical long passphrase"
    history = PasswordHistory.objects.create(
        user=user, password_hash=make_password(historical)
    )
    previous_hash = user.password
    viewer = Client()
    viewer.post("/login/", {"login": "reader", "password": PASSWORD})
    client.post("/login/", {"login": "ADMIN", "password": PASSWORD})
    response = client.post(f"/management/users/{user.pk}/reset/", {"confirm": "on"})
    secret = response.context["issued"].secret
    user.refresh_from_db()
    assert (
        user.password == previous_hash and user.password_history.get().pk == history.pk
    )
    assert viewer.get("/").url == "/login/"
    assert (
        viewer.post("/login/", {"login": "reader", "password": PASSWORD}).status_code
        == 200
    )
    assert CONTEXT_KEY not in viewer.session
    assert (
        viewer.post("/login/", {"login": "reader", "password": secret}).url
        == "/password/required/"
    )
    failed = viewer.post(
        "/password/required/",
        {"old_secret": secret, "new_secret": historical, "confirmation": historical},
    )
    assert "password_reused" in {
        error.code for error in failed.context["form"].errors.as_data()["new_secret"]
    }
    assert secret not in caplog.text + str(dict(client.session))
    assert secret not in client.get("/management/users/").text
    assert "no-store" in response.headers["Cache-Control"]


def test_unblock_never_restores_invalidated_session(
    admin_factory, user_factory, client
):
    admin_factory(password=PASSWORD, credential_mode="PERMANENT")
    user = user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    other = Client()
    other.post("/login/", {"login": "reader", "password": PASSWORD})
    client.post("/login/", {"login": "ADMIN", "password": PASSWORD})
    for action in ("block", "unblock"):
        client.post(f"/management/users/{user.pk}/{action}/", {"confirm": "on"})
    assert other.get("/").url == "/login/"
    assert other.post("/login/", {"login": "reader", "password": PASSWORD}).url == "/"


def test_layout_and_navigation_match_role(user_factory, client):
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    client.post("/login/", {"login": "reader", "password": PASSWORD})
    response = client.get("/")
    assert "Przejdź do treści" in response.text
    assert 'name="viewport"' in response.text
    assert "/management/users/" not in response.text
    assert "Dokumenty" in response.text
