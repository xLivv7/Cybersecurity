"""Account invariants exercised through model, manager and bulk ORM operations."""

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.accounts.models import CredentialMode, Role, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return User.objects.create_user(
        "ADMIN", role=Role.ADMINISTRATOR, credential_mode=CredentialMode.INITIAL
    )


def test_custom_user_is_installed_without_default_auth_user_table():
    assert get_user_model() is User
    assert User._meta.db_table in connection.introspection.table_names()
    assert "auth_user" not in connection.introspection.table_names()


@pytest.mark.parametrize(
    "role", [Role.MANAGER, Role.EDITOR, Role.EMPLOYEE, Role.READER]
)
def test_business_accounts_have_one_role_and_safe_initial_state(role):
    user = User.objects.create_user("employee", role=role)
    user.refresh_from_db()
    assert user.role == role
    assert user.credential_mode == CredentialMode.TEMPORARY
    assert user.session_version == 1
    assert user.password_changed_at is None
    assert user.deleted_at is None
    assert user.is_active
    assert not user.is_staff and not user.is_superuser
    assert not user.has_usable_password()


@pytest.mark.parametrize(
    ("original", "duplicate"),
    [(" Alice ", "alice"), ("Straße", "STRASSE"), ("ŻANETA", "żaneta")],
)
def test_login_is_unique_after_strip_and_unicode_casefold(original, duplicate):
    user = User.objects.create_user(original)
    assert user.username == original.strip()
    assert user.login_key == original.strip().casefold()
    assert User.objects.get_by_natural_key(f" {duplicate} ") == user
    with pytest.raises(ValidationError):
        User.objects.create_user(duplicate)
    assert User.objects.count() == 1


def test_normalizing_login_does_not_change_password_whitespace():
    password = "  a-long-educational-passphrase  "
    user = User.objects.create_user(" Reader ", password=password)
    assert user.check_password(password)
    assert not user.check_password(password.strip())
    assert user.password.startswith("argon2$argon2id$")


def test_admin_is_canonical_and_has_no_framework_privileges():
    user = User.objects.create_user(" admin ", role=Role.ADMINISTRATOR)
    assert user.username == "ADMIN" and user.login_key == "admin"
    assert user.role == Role.ADMINISTRATOR
    assert user.is_active and user.deleted_at is None
    assert not user.is_superuser and not user.is_staff


@pytest.mark.parametrize(
    ("username", "role"),
    [("ADMIN", Role.READER), ("admin", Role.EMPLOYEE), ("other", Role.ADMINISTRATOR)],
)
def test_reserved_login_and_administrator_role_cannot_be_separated(username, role):
    with pytest.raises(ValidationError):
        User.objects.create_user(username, role=role)
    assert not User.objects.exists()


@pytest.mark.parametrize("username", ["employee", "ADMIN"])
def test_saved_login_cannot_be_renamed(username):
    role = Role.ADMINISTRATOR if username == "ADMIN" else Role.READER
    user = User.objects.create_user(username, role=role)
    user.username = "renamed"
    with pytest.raises(ValidationError):
        user.save()
    user.refresh_from_db()
    assert user.username == username
    # An instance reconstructed with the same primary key cannot bypass the guard.
    replacement = User(pk=user.pk, username="replacement", role=role)
    with pytest.raises(ValidationError):
        replacement.save()
    user.refresh_from_db()
    assert user.username == username


@pytest.mark.parametrize("field", ["username", "login_key"])
def test_queryset_cannot_change_identity(field):
    user = User.objects.create_user("employee")
    with pytest.raises(ValidationError):
        User.objects.filter(pk=user.pk).update(**{field: "changed"})
    user.refresh_from_db()
    assert user.username == "employee" and user.login_key == "employee"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("role", Role.READER),
        ("is_active", False),
        ("deleted_at", "now"),
        ("is_staff", True),
        ("is_superuser", True),
    ],
)
def test_admin_protection_in_model_and_database(admin, field, value):
    value = timezone.now() if value == "now" else value
    setattr(admin, field, value)
    with pytest.raises(ValidationError):
        admin.save()
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=admin.pk).update(**{field: value})
    admin.refresh_from_db()
    assert admin.role == Role.ADMINISTRATOR
    assert admin.is_active and admin.deleted_at is None
    assert not admin.is_staff and not admin.is_superuser


@pytest.mark.parametrize("method", ["instance", "queryset", "base_manager", "mixed"])
def test_admin_cannot_be_physically_deleted_through_orm(admin, method):
    other = User.objects.create_user("reader")
    with pytest.raises(ProtectedError):
        if method == "instance":
            admin.login_key = "changed-in-memory"
            admin.delete()
        elif method == "queryset":
            User.objects.filter(pk=admin.pk).delete()
        elif method == "base_manager":
            User._base_manager.filter(pk=admin.pk).delete()
        else:
            User.objects.all().delete()
    assert User.objects.filter(pk=admin.pk).exists()
    assert User.objects.filter(pk=other.pk).exists()


def test_logically_deleted_login_stays_reserved():
    user = User.objects.create_user("reader")
    user.is_active = False
    user.deleted_at = timezone.now()
    user.save()
    with pytest.raises(ValidationError):
        User.objects.create_user("READER")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(is_active=True)


@pytest.mark.parametrize("field", ["is_staff", "is_superuser"])
def test_business_account_cannot_gain_framework_privileges(field):
    with pytest.raises(ValidationError):
        User.objects.create_user("reader", **{field: True})
    user = User.objects.create_user("reader")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(**{field: True})


def test_create_superuser_is_disabled_in_sync_and_async_manager():
    with pytest.raises(ValueError):
        User.objects.create_superuser("ADMIN")
    with pytest.raises(ValueError):
        async_to_sync(User.objects.acreate_superuser)("ADMIN")
    assert not User.objects.exists()


def test_bulk_creation_preserves_login_uniqueness():
    users = User.objects.bulk_create([User(username=" Straße ")])
    assert users[0].login_key == "strasse"
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create([User(username="STRASSE")])


def test_bulk_operations_do_not_bypass_admin_or_rename_guards(admin):
    with pytest.raises(ValidationError):
        User.objects.bulk_create([User(username="other", role=Role.ADMINISTRATOR)])
    admin.username = "renamed"
    with pytest.raises(ValidationError):
        User.objects.bulk_update([admin], ["username"])
    admin.refresh_from_db()
    admin.role = Role.READER
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_update([admin], ["role"])
    admin.refresh_from_db()
    assert admin.role == Role.ADMINISTRATOR


@pytest.mark.parametrize(
    "changes",
    [
        {"role": "UNKNOWN"},
        {"credential_mode": "UNKNOWN"},
        {"credential_mode": CredentialMode.INITIAL},
        {"session_version": 0},
    ],
)
def test_invalid_role_credential_state_or_session_version_is_rejected(changes):
    with pytest.raises(ValidationError):
        User.objects.create_user("reader", **changes)
    user = User.objects.create_user("reader")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(**changes)
