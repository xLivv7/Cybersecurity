"""Storage invariants for permanent history and temporary credentials."""

from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError

from apps.security.constants import TEMPORARY_PASSWORD_LIFETIME
from apps.security.models import PasswordHistory, TemporaryCredential

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def encoded_password():
    return make_password("example-long-secret")


@pytest.fixture
def credential_data(user_factory, clock, encoded_password):
    user = user_factory()
    return {
        "user": user,
        "password_hash": encoded_password,
        "issued_at": clock.now(),
        "expires_at": clock.now() + TEMPORARY_PASSWORD_LIFETIME,
        "credential_version": user.session_version,
    }


def test_history_records_only_hash_and_replacement_time(
    user_factory, clock, encoded_password
):
    user = user_factory()
    history = PasswordHistory.objects.create(user=user, password_hash=encoded_password)
    history.refresh_from_db()
    assert history.password_hash == encoded_password
    assert history.replaced_at == clock.now()
    assert check_password("example-long-secret", history.password_hash)
    assert user.password_history.get() == history
    assert {field.name for field in PasswordHistory._meta.fields} == {
        "id",
        "user",
        "password_hash",
        "replaced_at",
    }


def test_hashes_use_argon2id_and_random_salts():
    first = make_password("example-long-secret")
    second = make_password("example-long-secret")
    assert first.startswith("argon2$argon2id$")
    assert second.startswith("argon2$argon2id$")
    assert first != second
    assert check_password("example-long-secret", first)
    assert check_password("example-long-secret", second)


@pytest.mark.parametrize("model", [PasswordHistory, TemporaryCredential])
@pytest.mark.parametrize(
    "invalid", ["plain-secret", "", "!unusable", "argon2$argon2id$bad"]
)
def test_models_reject_raw_or_invalid_hashes(model, invalid, credential_data):
    fields = {"user": credential_data["user"], "password_hash": invalid}
    if model is TemporaryCredential:
        fields = {**credential_data, "password_hash": invalid}
    with pytest.raises(ValidationError):
        model.objects.create(**fields)
    assert not model.objects.exists()


def test_bulk_and_queryset_writes_cannot_store_plain_passwords(credential_data):
    credential = TemporaryCredential.objects.create(**credential_data)
    with transaction.atomic(), pytest.raises(ValidationError):
        TemporaryCredential.objects.filter(pk=credential.pk).update(
            password_hash="plain-secret"
        )
    with transaction.atomic(), pytest.raises(ValidationError):
        PasswordHistory.objects.bulk_create(
            [PasswordHistory(user=credential.user, password_hash="plain-secret")]
        )
    credential.refresh_from_db()
    assert credential.password_hash == credential_data["password_hash"]


def test_temporary_credential_lifecycle_storage(credential_data, clock):
    credential = TemporaryCredential.objects.create(**credential_data)
    assert credential.consumed_at is None and credential.revoked_at is None
    assert credential.expires_at - credential.issued_at == timedelta(hours=4)
    assert credential.user.temporary_credentials.get() == credential
    clock.advance(timedelta(minutes=1))
    credential.consumed_at = clock.now()
    credential.save()
    clock.advance(timedelta(minutes=1))
    credential.revoked_at = clock.now()
    credential.save()
    credential.refresh_from_db()
    assert credential.consumed_at < credential.revoked_at
    assert check_password("example-long-secret", credential.password_hash)
    assert {field.name for field in TemporaryCredential._meta.fields} == {
        "id",
        "user",
        "password_hash",
        "issued_at",
        "expires_at",
        "consumed_at",
        "revoked_at",
        "credential_version",
    }


@pytest.mark.parametrize(
    "invalid_state",
    [
        "zero_version",
        "expiry_before_issue",
        "expiry_at_issue",
        "consumed_before_issue",
        "consumed_at_expiry",
        "consumed_after_expiry",
        "revoked_before_issue",
    ],
)
def test_invalid_lifecycle_rejected_by_model_and_database(
    invalid_state, credential_data
):
    credential = TemporaryCredential.objects.create(**credential_data)
    issued = credential.issued_at
    expired = credential.expires_at
    changes = {
        "zero_version": {"credential_version": 0},
        "expiry_before_issue": {"expires_at": issued - timedelta(seconds=1)},
        "expiry_at_issue": {"expires_at": issued},
        "consumed_before_issue": {"consumed_at": issued - timedelta(seconds=1)},
        "consumed_at_expiry": {"consumed_at": expired},
        "consumed_after_expiry": {"consumed_at": expired + timedelta(seconds=1)},
        "revoked_before_issue": {"revoked_at": issued - timedelta(seconds=1)},
    }[invalid_state]
    for field, value in changes.items():
        setattr(credential, field, value)
    with pytest.raises(ValidationError):
        credential.save()
    with transaction.atomic(), pytest.raises(IntegrityError):
        TemporaryCredential.objects.filter(pk=credential.pk).update(**changes)


def test_credential_version_unique_per_account(credential_data, user_factory):
    TemporaryCredential.objects.create(**credential_data)
    with pytest.raises(ValidationError):
        TemporaryCredential.objects.create(**credential_data)
    with transaction.atomic(), pytest.raises(IntegrityError):
        TemporaryCredential.objects.bulk_create(
            [TemporaryCredential(**credential_data)]
        )
    TemporaryCredential.objects.create(**{**credential_data, "user": user_factory()})


def test_repeated_reset_generations_leave_permanent_hash_and_history_intact(
    credential_data, encoded_password, clock
):
    # Exercise the data representation only; the reset service belongs to T009.
    user = credential_data["user"]
    user.password = encoded_password
    user.credential_mode = user.CredentialMode.PERMANENT
    user.save()
    history = PasswordHistory.objects.create(user=user, password_hash=encoded_password)
    original = (history.pk, history.password_hash, history.replaced_at)
    for version in range(2, 5):
        TemporaryCredential.objects.filter(user=user, revoked_at__isnull=True).update(
            revoked_at=clock.now()
        )
        user.session_version = version
        user.credential_mode = user.CredentialMode.TEMPORARY
        user.save()
        TemporaryCredential.objects.create(
            **{
                **credential_data,
                "issued_at": clock.now(),
                "expires_at": clock.now() + TEMPORARY_PASSWORD_LIFETIME,
                "credential_version": version,
            }
        )
        clock.advance(timedelta(minutes=1))
    user.refresh_from_db()
    history.refresh_from_db()
    assert user.password == encoded_password
    assert (history.pk, history.password_hash, history.replaced_at) == original
    assert user.password_history.count() == 1
    assert user.temporary_credentials.count() == 3
    assert user.temporary_credentials.filter(revoked_at__isnull=True).count() == 1


def test_history_orders_newest_first_with_stable_ties(
    user_factory, encoded_password, clock
):
    user = user_factory()
    first = PasswordHistory.objects.create(user=user, password_hash=encoded_password)
    second = PasswordHistory.objects.create(user=user, password_hash=encoded_password)
    clock.advance(timedelta(minutes=1))
    third = PasswordHistory.objects.create(user=user, password_hash=encoded_password)
    assert list(user.password_history.all()) == [third, second, first]


@pytest.mark.parametrize("model", [PasswordHistory, TemporaryCredential])
def test_logical_deletion_retains_credentials_and_physical_deletion_is_protected(
    model, credential_data, clock
):
    user = credential_data["user"]
    fields = (
        credential_data
        if model is TemporaryCredential
        else {"user": user, "password_hash": credential_data["password_hash"]}
    )
    record = model.objects.create(**fields)
    user.is_active = False
    user.deleted_at = clock.now()
    user.save()
    record.refresh_from_db()
    assert record.user_id == user.pk
    with pytest.raises(ProtectedError):
        user.delete()


@pytest.mark.django_db(transaction=True)
def test_credentials_migration_from_empty_security_schema():
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("security", None)])
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        apps = executor.loader.project_state(latest).apps
        for model in ("PasswordHistory", "TemporaryCredential"):
            historical = apps.get_model("security", model)
            assert historical._meta.db_table in connection.introspection.table_names()
            assert historical.objects.count() == 0
        assert apps.get_model("security", "SecuritySettings").objects.count() == 1
    finally:
        MigrationExecutor(connection).migrate(latest)
