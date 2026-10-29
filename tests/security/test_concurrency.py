"""Independent SQLite file connections exercise real races and lock failures."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event, current_thread

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import connections, transaction
from django.db.models import QuerySet

from apps.security import services
from apps.security.models import PasswordHistory, TemporaryCredential
from apps.security.selectors import get_security_settings
from apps.security.services import (
    ChangeReason,
    SecurityConflict,
    change_password,
    consume_temporary_credential,
    issue_temporary_credential,
    verify_permanent_password,
    verify_temporary_credential,
)


def worker(operation):
    try:
        # Each thread has its own Django wrapper and underlying sqlite connection.
        with connections["default"].cursor() as cursor:
            cursor.execute("PRAGMA database_list")
            database_file = cursor.fetchone()[2]
        try:
            result = operation()
            return "success", result, database_file
        except SecurityConflict:
            return "conflict", None, database_file
    finally:
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_two_connections_can_consume_only_once(file_database, monkeypatch):
    user = get_user_model().objects.create_user("race-user")
    issued = issue_temporary_credential(user.pk)
    barrier = Barrier(2)
    original_check = services.check_password

    def synchronize(*args, **kwargs):
        result = original_check(*args, **kwargs)
        barrier.wait(timeout=15)
        return result

    monkeypatch.setattr(services, "check_password", synchronize)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                worker,
                lambda: consume_temporary_credential(
                    issued.credential_id, issued.secret
                ),
            )
            for _ in range(2)
        ]
        results = [future.result(timeout=30) for future in futures]
    assert sorted(item[0] for item in results) == ["conflict", "success"]
    assert all(item[2] == file_database for item in results)
    assert (
        TemporaryCredential.objects.get(pk=issued.credential_id).consumed_at is not None
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("operation", ["consume", "change"])
def test_reset_wins_against_prevalidated_old_state(
    file_database, monkeypatch, operation
):
    User = get_user_model()
    user = User.objects.create_user(
        "race-user", password="previous long passphrase", credential_mode="PERMANENT"
    )
    issued = issue_temporary_credential(user.pk)
    if operation == "change":
        consume_temporary_credential(issued.credential_id, issued.secret)
    validated, release = Event(), Event()
    function_name = "check_password" if operation == "consume" else "make_password"
    original_function = getattr(services, function_name)

    def pause_after_validation(*args, **kwargs):
        value = original_function(*args, **kwargs)
        if current_thread().name.startswith("race"):
            validated.set()
            assert release.wait(timeout=20)
        return value

    monkeypatch.setattr(services, function_name, pause_after_validation)

    def old_operation():
        if operation == "consume":
            return consume_temporary_credential(issued.credential_id, issued.secret)
        return change_password(
            user.pk,
            issued.secret,
            "completely different new passphrase",
            "completely different new passphrase",
            reason=ChangeReason.RESET,
            expected_version=issued.version,
            credential_id=issued.credential_id,
        )

    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="race") as executor:
        future = executor.submit(worker, old_operation)
        try:
            assert validated.wait(timeout=20)
            newest = issue_temporary_credential(user.pk)
        finally:
            release.set()
        assert future.result(timeout=30)[0] == "conflict"
    user.refresh_from_db()
    assert user.session_version == newest.version
    assert user.credential_mode == "TEMPORARY"
    assert user.password_history.count() == 0
    assert verify_temporary_credential(newest.credential_id, newest.secret)
    assert not verify_temporary_credential(issued.credential_id, issued.secret)


@pytest.mark.django_db
def test_zero_row_consumption_never_returns_access_context(user_factory, monkeypatch):
    issued = issue_temporary_credential(user_factory().pk)
    original_update = QuerySet.update

    def no_winner(queryset, **kwargs):
        if queryset.model is TemporaryCredential and "consumed_at" in kwargs:
            return 0
        return original_update(queryset, **kwargs)

    monkeypatch.setattr(QuerySet, "update", no_winner)
    with pytest.raises(SecurityConflict):
        consume_temporary_credential(issued.credential_id, issued.secret)
    assert TemporaryCredential.objects.get(pk=issued.credential_id).consumed_at is None


@pytest.mark.django_db
def test_reset_during_permanent_password_check_rejects_stale_success(
    user_factory, monkeypatch
):
    user = user_factory(
        password="previous long passphrase", credential_mode="PERMANENT"
    )
    original_check = services.check_password

    def reset_after_check(*args, **kwargs):
        result = original_check(*args, **kwargs)
        issue_temporary_credential(user.pk)
        return result

    monkeypatch.setattr(services, "check_password", reset_after_check)
    assert not verify_permanent_password(user.pk, "previous long passphrase")


@pytest.mark.django_db
def test_recovering_initial_admin_does_not_archive_operator_secret(admin_factory):
    user = admin_factory(password="initial operator passphrase")
    issued = issue_temporary_credential(user.pk)
    consume_temporary_credential(issued.credential_id, issued.secret)
    change_password(
        user.pk,
        issued.secret,
        "completely different new passphrase",
        "completely different new passphrase",
        reason=ChangeReason.RESET,
        expected_version=issued.version,
        credential_id=issued.credential_id,
    )
    assert user.password_history.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("operation", ["issue", "consume", "change"])
def test_database_write_lock_returns_conflict_without_partial_state(
    file_database, operation
):
    user = get_user_model().objects.create_user("race-user")
    issued = issue_temporary_credential(user.pk)
    if operation == "change":
        consume_temporary_credential(issued.credential_id, issued.secret)
    locked, release = Event(), Event()

    def hold_write_lock():
        with transaction.atomic():
            locked.set()
            assert release.wait(timeout=20)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(worker, hold_write_lock)
        try:
            assert locked.wait(timeout=10)
            with pytest.raises(SecurityConflict):
                if operation == "issue":
                    issue_temporary_credential(user.pk)
                elif operation == "consume":
                    consume_temporary_credential(issued.credential_id, issued.secret)
                else:
                    change_password(
                        user.pk,
                        issued.secret,
                        "completely different new passphrase",
                        "completely different new passphrase",
                        reason=ChangeReason.RESET,
                        expected_version=issued.version,
                        credential_id=issued.credential_id,
                    )
        finally:
            release.set()
        assert future.result(timeout=30)[0] == "success"
    user.refresh_from_db()
    credential = TemporaryCredential.objects.get(pk=issued.credential_id)
    assert user.session_version == issued.version
    assert user.credential_mode == "TEMPORARY"
    assert user.password_history.count() == 0
    assert user.temporary_credentials.count() == 1
    assert credential.revoked_at is None
    assert (credential.consumed_at is not None) == (operation == "change")


@pytest.mark.django_db
def test_consumption_boundary_and_repeat(user_factory, clock):
    issued = issue_temporary_credential(user_factory().pk)
    with pytest.raises(ValidationError):
        consume_temporary_credential(issued.credential_id, "wrong")
    clock.set(issued.expires_at - timedelta(microseconds=1))
    result = consume_temporary_credential(issued.credential_id, issued.secret)
    assert result.version == issued.version
    assert result.expires_at == issued.expires_at
    with pytest.raises(SecurityConflict):
        consume_temporary_credential(issued.credential_id, issued.secret)
    expired = issue_temporary_credential(issued.user_id)
    clock.set(expired.expires_at)
    with pytest.raises(SecurityConflict):
        consume_temporary_credential(expired.credential_id, expired.secret)


@pytest.mark.django_db
def test_deadline_crossed_during_hash_check_is_rejected(
    user_factory, clock, monkeypatch
):
    issued = issue_temporary_credential(user_factory().pk)
    original_check = services.check_password

    def expire(*args, **kwargs):
        result = original_check(*args, **kwargs)
        clock.set(issued.expires_at)
        return result

    monkeypatch.setattr(services, "check_password", expire)
    with pytest.raises(SecurityConflict):
        consume_temporary_credential(issued.credential_id, issued.secret)
    assert TemporaryCredential.objects.get(pk=issued.credential_id).consumed_at is None


@pytest.mark.django_db
@pytest.mark.parametrize("modified_source", ["policy", "history", "credential"])
def test_change_rechecks_sources_after_expensive_hashing(
    modified_source, user_factory, clock, monkeypatch
):
    user = user_factory()
    issued = issue_temporary_credential(user.pk)
    consume_temporary_credential(issued.credential_id, issued.secret)
    original_make = services.make_password

    def mutate(*args, **kwargs):
        encoded = original_make(*args, **kwargs)
        if modified_source == "policy":
            policy = get_security_settings()
            policy.levenshtein_enabled = not policy.levenshtein_enabled
            policy.save()
        elif modified_source == "history":
            PasswordHistory.objects.create(
                user=user, password_hash=make_password("another retired phrase")
            )
        else:
            TemporaryCredential.objects.filter(pk=issued.credential_id).update(
                revoked_at=clock.now()
            )
        return encoded

    monkeypatch.setattr(services, "make_password", mutate)
    with pytest.raises(SecurityConflict):
        change_password(
            user.pk,
            issued.secret,
            "completely different new passphrase",
            "completely different new passphrase",
            reason=ChangeReason.RESET,
            expected_version=issued.version,
            credential_id=issued.credential_id,
        )
    user.refresh_from_db()
    assert user.session_version == issued.version
    assert user.credential_mode == "TEMPORARY"
