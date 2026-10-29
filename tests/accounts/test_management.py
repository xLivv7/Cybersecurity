"""Local administrator commands and the complete account panel."""

from io import StringIO

import pytest
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client

from apps.accounts.management.commands import init_admin
from apps.accounts.models import User
from apps.accounts.services import account_action, create_account, edit_account
from apps.security.models import PasswordHistory
from apps.security.selectors import get_security_settings

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("captcha_success")]
PASSWORD = "previous long passphrase"


@pytest.fixture
def manager_admin(admin_factory, client):
    actor = admin_factory(password=PASSWORD, credential_mode="PERMANENT")
    client.post("/login/", {"login": "ADMIN", "password": PASSWORD})
    return actor


def test_init_and_recover_admin_preserve_identity_and_require_confirmation(monkeypatch):
    inputs = iter([PASSWORD, PASSWORD])
    monkeypatch.setattr(init_admin, "getpass", lambda prompt: next(inputs))
    output = StringIO()
    call_command("init_admin", stdout=output)
    user = User.objects.get(username="ADMIN")
    assert user.credential_mode == "INITIAL" and user.check_password(PASSWORD)
    assert PASSWORD not in output.getvalue()
    with pytest.raises(CommandError):
        call_command("init_admin", stdout=output)
    monkeypatch.setattr("builtins.input", lambda prompt: "no")
    with pytest.raises(CommandError):
        call_command("recover_admin", stdout=output)
    monkeypatch.setattr("builtins.input", lambda prompt: "ADMIN")
    output = StringIO()
    call_command("recover_admin", stdout=output)
    secret = output.getvalue().strip().split()[-1]
    user.refresh_from_db()
    assert user.credential_mode == "TEMPORARY" and user.session_version == 2
    assert check_password(secret, user.temporary_credentials.get().password_hash)
    assert len(secret) == 16


@pytest.mark.parametrize("values", [("short", "short"), (PASSWORD, "different")])
def test_init_rejects_bad_passwords_without_partial_account(values, monkeypatch):
    inputs = iter(values)
    monkeypatch.setattr(init_admin, "getpass", lambda prompt: next(inputs))
    with pytest.raises(CommandError):
        call_command("init_admin", stdout=StringIO())
    assert not User.objects.exists()


def test_create_edit_block_delete_and_reset_services(
    manager_admin, user_factory, clock
):
    user, issued = create_account(manager_admin, username="reader", role="READER")
    assert user.session_version == 2
    user.refresh_from_db()
    assert user.session_version == issued.version == 2
    user.password = make_password(PASSWORD)
    user.save()
    history = PasswordHistory.objects.create(
        user=user, password_hash=make_password("historical permanent phrase")
    )
    edit_account(
        manager_admin, user.pk, first_name="Anna", last_name="Testowa", role="EMPLOYEE"
    )
    user.refresh_from_db()
    assert user.session_version == 3 and user.role == "EMPLOYEE"
    for action in ("block", "unblock", "reset"):
        account_action(manager_admin, user.pk, action)
    user.refresh_from_db()
    assert user.is_active and user.session_version == 6
    assert user.password_history.get().pk == history.pk
    account_action(manager_admin, user.pk, "delete")
    user.refresh_from_db()
    assert user.deleted_at == clock.now() and not user.is_active
    with pytest.raises(ValidationError):
        user_factory("READER")
    for action in ("block", "unblock", "delete", "reset"):
        with pytest.raises(ValidationError):
            account_action(manager_admin, manager_admin.pk, action)
    with pytest.raises(ValidationError):
        edit_account(
            manager_admin, manager_admin.pk, first_name="", last_name="", role="READER"
        )


def test_panel_whitelists_fields_and_presents_secret_once(manager_admin, client):
    response = client.post(
        "/management/users/new/",
        {
            "username": "reader",
            "role": "READER",
            "first_name": "Anna",
            "last_name": "Testowa",
            "is_superuser": "1",
            "session_version": "999",
            "password": "injected",
        },
    )
    assert response.status_code == 200
    secret = response.context["issued"].secret
    user = User.objects.get(username="reader")
    assert not user.is_superuser and user.session_version == 2
    assert "no-store" in response.headers["Cache-Control"]
    assert secret not in str(dict(client.session))
    assert secret not in client.get("/management/users/").text
    before = user.session_version
    confirm = f"/management/users/{user.pk}/block/"
    assert "Konto utraci dostęp" in client.get(confirm).text
    client.post(confirm, {})
    user.refresh_from_db()
    assert user.session_version == before
    client.post(confirm, {"confirm": "on"})
    user.refresh_from_db()
    assert not user.is_active


@pytest.mark.parametrize("role", ["MANAGER", "EDITOR", "EMPLOYEE", "READER"])
def test_other_roles_cannot_manage_accounts(role, user_factory, client):
    user = user_factory(
        "reader", password=PASSWORD, role=role, credential_mode="PERMANENT"
    )
    client.post("/login/", {"login": "reader", "password": PASSWORD})
    for path in (
        "/management/users/",
        "/management/users/new/",
        "/management/security/",
    ):
        assert client.get(path).status_code == 403
        assert (
            client.post(path, {"username": "injected", "role": "ADMIN"}).status_code
            == 403
        )
    with pytest.raises(PermissionDenied):
        create_account(user, username="injected", role="READER")


def test_admin_forms_csrf_and_policy_validation(manager_admin, user_factory, client):
    user = user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    viewer = Client()
    viewer.post("/login/", {"login": "reader", "password": PASSWORD})
    client.post(
        f"/management/users/{user.pk}/edit/",
        {
            "first_name": "Test",
            "last_name": "",
            "role": "EMPLOYEE",
            "username": "changed",
        },
    )
    assert viewer.get("/").url == "/login/"
    user.refresh_from_db()
    assert user.username == "reader"
    policy = get_security_settings()
    for days, minutes in [("1.5", "15"), ("-1", "15"), ("0", "0")]:
        response = client.post(
            "/management/security/",
            {
                "password_max_age_days": days,
                "idle_timeout_minutes": minutes,
                "login_failure_limit": "5",
            },
        )
        assert response.context["form"].errors
        assert (
            get_security_settings().idle_timeout_minutes == policy.idle_timeout_minutes
        )
    assert (
        client.post(
            "/management/security/",
            {
                "password_max_age_days": "0",
                "idle_timeout_minutes": "5",
                "login_failure_limit": "5",
            },
        ).status_code
        == 302
    )
    assert get_security_settings().idle_timeout_minutes == 5
    protected = Client(enforce_csrf_checks=True)
    protected.cookies = client.cookies
    for path in (
        "/management/users/new/",
        f"/management/users/{user.pk}/delete/",
        "/management/security/",
    ):
        assert protected.post(path, {"confirm": "on"}).status_code == 403
