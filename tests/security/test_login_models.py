"""Policy, opaque identities and additive migrations for login protection."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Value

from apps.documents.models import Document
from apps.security.constants import LOGIN_LOCK_SECONDS
from apps.security.login_keys import login_identity_key
from apps.security.models import (
    LoginAttemptState,
    PasswordHistory,
    SecurityEvent,
    TemporaryCredential,
)
from apps.security.selectors import get_security_settings
from apps.security.services import issue_temporary_credential

pytestmark = pytest.mark.django_db


def test_defaults_and_normalized_private_identity():
    assert get_security_settings().login_failure_limit == 5
    assert LOGIN_LOCK_SECONDS == 900
    key = login_identity_key(" ŻANETA ")
    assert key == login_identity_key("żaneta")
    assert len(key) == 64 and "żaneta" not in key
    assert key != login_identity_key("other")
    LoginAttemptState.objects.create(identity_key=key)
    with transaction.atomic(), pytest.raises(IntegrityError):
        LoginAttemptState.objects.bulk_create([LoginAttemptState(identity_key=key)])


@pytest.mark.parametrize(
    "value", [0, -1, 1.5, Decimal("1.5"), "1.5", True, None, "abc"]
)
def test_invalid_threshold_is_not_saved(value):
    policy = get_security_settings()
    policy.login_failure_limit = value
    with pytest.raises(ValidationError):
        policy.save()
    assert get_security_settings().login_failure_limit == 5


@pytest.mark.parametrize("value", [0, -1, Value(1.5)])
def test_threshold_database_constraint(value):
    from apps.security.models import SecuritySettings

    with transaction.atomic(), pytest.raises(IntegrityError):
        SecuritySettings.objects.update(login_failure_limit=value)


def test_counter_and_event_validation(clock):
    key = login_identity_key("absent")
    state = LoginAttemptState(identity_key=key, failure_count=-1)
    with pytest.raises(ValidationError):
        state.save()
    state.failure_count = 0
    state.blocked_until = clock.now() + timedelta(seconds=900)
    with pytest.raises(ValidationError):
        state.save()
    with transaction.atomic(), pytest.raises(IntegrityError):
        LoginAttemptState.objects.bulk_create([state])
    with pytest.raises(ValidationError):
        LoginAttemptState(identity_key="submitted login or password").save()
    event = SecurityEvent.objects.create(
        category=SecurityEvent.Category.CREDENTIAL_FAILURE, identity_key=key
    )
    assert event.created_at == clock.now()
    assert {f.name for f in event._meta.fields} == {
        "id",
        "category",
        "identity_key",
        "created_at",
    }
    with pytest.raises(ValidationError):
        SecurityEvent.objects.create(category="untrusted payload", identity_key=key)
    with transaction.atomic(), pytest.raises(IntegrityError):
        SecurityEvent.objects.bulk_create(
            [SecurityEvent(category="untrusted payload", identity_key=key)]
        )


@pytest.mark.django_db(transaction=True)
def test_migration_preserves_accounts_credentials_documents_and_policy(user_factory):
    user = user_factory("migration-reader", password="previous long passphrase")
    issue_temporary_credential(user.pk)
    Document.objects.create(title="Existing", body="Saved text", author=user)
    models = [type(user), PasswordHistory, TemporaryCredential, Document]
    snapshots = [list(model.objects.values()) for model in models]
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    before = [("security", "0003_passwordhistory_temporarycredential")]
    try:
        executor.migrate(before)
        historical = executor.loader.project_state(before).apps
        Policy = historical.get_model("security", "SecuritySettings")
        Policy.objects.update_or_create(
            pk=1,
            defaults={
                "levenshtein_enabled": False,
                "password_max_age_days": 7,
                "idle_timeout_minutes": 3,
            },
        )
        previous = Policy.objects.values().get(pk=1)
        MigrationExecutor(connection).migrate(latest)
        current = get_security_settings()
        assert current.login_failure_limit == 5
        for name, value in previous.items():
            assert getattr(current, name) == value
        for model, snapshot in zip(models, snapshots, strict=True):
            assert list(model.objects.values()) == snapshot
        assert not LoginAttemptState.objects.exists()
        assert not SecurityEvent.objects.exists()
    finally:
        MigrationExecutor(connection).migrate(latest)


@pytest.mark.django_db(transaction=True)
def test_migration_initializes_empty_security_schema():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("security", None)])
        MigrationExecutor(connection).migrate(latest)
        assert get_security_settings().login_failure_limit == 5
        assert LoginAttemptState.objects.count() == SecurityEvent.objects.count() == 0
    finally:
        MigrationExecutor(connection).migrate(latest)
