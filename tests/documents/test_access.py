"""Full role, state and ownership matrix tested through real HTTP requests."""

import pytest
from django.contrib.auth.hashers import make_password
from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError

from apps.accounts.models import User
from apps.documents.models import Document
from apps.documents.policies import can
from apps.documents.services import edit_document
from apps.security.services import issue_temporary_credential

pytestmark = pytest.mark.django_db
PASSWORD = "previous long passphrase"


@pytest.fixture(scope="module")
def encoded():
    return make_password(PASSWORD)


def expected(role, operation, status, own):
    if operation == "read":
        return (
            status == "PUBLISHED"
            or role in ("MANAGER", "EDITOR")
            or (role == "EMPLOYEE" and own)
        )
    if operation == "create":
        return role in ("MANAGER", "EDITOR", "EMPLOYEE")
    if operation == "edit":
        return status == "DRAFT" and (
            role in ("MANAGER", "EDITOR") or (role == "EMPLOYEE" and own)
        )
    if operation == "publish":
        return role == "MANAGER" and status == "DRAFT"
    if operation == "withdraw":
        return role == "MANAGER" and status == "PUBLISHED"
    return False


@pytest.mark.parametrize("role", User.Role.values)
@pytest.mark.parametrize("status", Document.Status.values)
@pytest.mark.parametrize("own", [False, True])
def test_matrix_through_http(role, status, own, user_factory, client, encoded):
    user = user_factory(
        "ADMIN" if role == "ADMIN" else "actor", role=role, credential_mode="PERMANENT"
    )
    User.objects.filter(pk=user.pk).update(password=encoded)
    other = user_factory("other")
    document = Document.objects.create(
        title="Private document marker",
        body="Hidden body marker",
        author=user if own else other,
        status=status,
    )
    client.post("/login/", {"login": user.username, "password": PASSWORD})
    listing = client.get("/documents/")
    allowed_read = expected(role, "read", status, own)
    assert (document.title in listing.text) == allowed_read
    for operation in ("read", "edit", "publish", "withdraw", "create", "delete"):
        assert can(user, operation, document) == expected(role, operation, status, own)
    detail = client.get(f"/documents/{document.pk}/")
    assert detail.status_code == (200 if allowed_read else 403)
    if not allowed_read:
        assert document.title not in detail.text and document.body not in detail.text
    assert client.get("/documents/999999/").status_code == 404
    assert client.post(
        "/documents/new/",
        {"title": "Created", "body": "Text", "author": other.pk, "status": "PUBLISHED"},
    ).status_code == (302 if expected(role, "create", status, own) else 403)
    if expected(role, "create", status, own):
        new = Document.objects.get(title="Created")
        assert new.author_id == user.pk and new.status == "DRAFT"
    response = client.post(
        f"/documents/{document.pk}/edit/",
        {
            "title": "Edited",
            "body": "New body",
            "author": user.pk,
            "status": "PUBLISHED",
        },
    )
    assert response.status_code == (302 if expected(role, "edit", status, own) else 403)
    document.refresh_from_db()
    assert document.status == status
    assert document.title == (
        "Edited" if expected(role, "edit", status, own) else "Private document marker"
    )
    for operation in ("publish", "withdraw"):
        Document.objects.filter(pk=document.pk).update(status=status)
        assert client.get(f"/documents/{document.pk}/{operation}/").status_code == 405
        response = client.post(f"/documents/{document.pk}/{operation}/")
        assert response.status_code == (
            302 if expected(role, operation, status, own) else 403
        )
        document.refresh_from_db()
        if not expected(role, operation, status, own):
            assert document.status == status


def test_text_is_escaped_and_authentication_cannot_be_bypassed(user_factory, client):
    user = user_factory(
        "manager", role="MANAGER", password=PASSWORD, credential_mode="PERMANENT"
    )
    document = Document.objects.create(
        author=user, title="<script>alert(1)</script>", body="<script>alert(2)</script>"
    )
    response = client.get(f"/documents/{document.pk}/")
    assert response.status_code == 302 and response.url.startswith("/login/")
    client.post("/login/", {"login": "manager", "password": PASSWORD})
    response = client.get(f"/documents/{document.pk}/")
    assert "<script>" not in response.text and "&lt;script&gt;" in response.text
    issued = issue_temporary_credential(user.pk)
    client.post("/login/", {"login": "manager", "password": issued.secret})
    assert client.get(f"/documents/{document.pk}/").url == "/password/required/"
    with pytest.raises(PermissionDenied):
        edit_document(user, document.pk, title="injected", body="injected")


def test_author_is_protected_and_logical_delete_retains_document(user_factory, clock):
    user = user_factory()
    document = Document.objects.create(title="Example", body="Text", author=user)
    assert document.status == "DRAFT"
    with pytest.raises(ProtectedError):
        user.delete()
    user.is_active = False
    user.deleted_at = clock.now()
    user.save()
    document.refresh_from_db()
    assert document.author_id == user.pk
