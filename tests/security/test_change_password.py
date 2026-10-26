"""All change paths share policy and an all-or-nothing persistence operation."""

from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError

from apps.security.models import PasswordHistory, TemporaryCredential
from apps.security.selectors import get_security_settings
from apps.security.services import (
    ChangeReason,
    SecurityConflict,
    change_password,
    issue_temporary_credential,
    verify_permanent_password,
)

pytestmark = pytest.mark.django_db
OLD = "previous long passphrase"
NEW = "completely different new passphrase"


def change(user, old=OLD, new=NEW, confirmation=None, **kwargs):
    return change_password(
        user.pk,
        old,
        new,
        new if confirmation is None else confirmation,
        reason=kwargs.pop("reason", ChangeReason.VOLUNTARY),
        expected_version=kwargs.pop("expected_version", user.session_version),
        **kwargs,
    )


@pytest.fixture
def permanent_user(user_factory, clock):
    return user_factory(
        password=OLD, credential_mode="PERMANENT", password_changed_at=clock.now()
    )


def test_voluntary_change_records_history_timestamp_and_invalidates_version(
    permanent_user, clock
):
    user = permanent_user
    encoded = user.password
    clock.advance(timedelta(days=1))
    result = change(user)
    user.refresh_from_db()
    assert user.session_version == result.version == 2
    assert user.password_changed_at == clock.now()
    assert verify_permanent_password(user.pk, NEW)
    assert not verify_permanent_password(user.pk, OLD)
    assert user.password_history.get().password_hash == encoded


@pytest.mark.parametrize(
    "old,new,confirmation",
    [
        ("wrong", NEW, NEW),
        (OLD, "short", "short"),
        (OLD, NEW, "mismatch"),
        (OLD, OLD, OLD),
    ],
)
def test_validation_failure_leaves_everything_unchanged(
    permanent_user, old, new, confirmation
):
    before = (
        permanent_user.password,
        permanent_user.password_changed_at,
        permanent_user.session_version,
    )
    with pytest.raises(ValidationError):
        change(permanent_user, old, new, confirmation)
    permanent_user.refresh_from_db()
    assert (
        permanent_user.password,
        permanent_user.password_changed_at,
        permanent_user.session_version,
    ) == before
    assert permanent_user.password_history.count() == 0


def test_write_failure_rolls_back_password_history_and_credential_revocation(
    permanent_user, clock, monkeypatch
):
    before = permanent_user.password
    credential = TemporaryCredential.objects.create(
        user=permanent_user,
        password_hash=make_password("temporary secret"),
        issued_at=clock.now(),
        expires_at=clock.now() + timedelta(hours=4),
        credential_version=1,
    )

    def fail(*args, **kwargs):
        raise RuntimeError("simulated history write failure")

    monkeypatch.setattr(PasswordHistory, "save", fail)
    with pytest.raises(RuntimeError):
        change(permanent_user)
    permanent_user.refresh_from_db()
    credential.refresh_from_db()
    assert permanent_user.password == before and permanent_user.session_version == 1
    assert permanent_user.password_history.count() == 0
    assert credential.revoked_at is None


def test_initial_admin_change_does_not_archive_initial_secret(admin_factory):
    user = admin_factory(password=OLD)
    change(user, reason=ChangeReason.INITIAL)
    user.refresh_from_db()
    assert user.credential_mode == "PERMANENT"
    assert check_password(NEW, user.password)
    assert user.password_history.count() == 0


def test_expired_change_and_context_enforcement(permanent_user, clock):
    policy = get_security_settings()
    policy.password_max_age_days = 1
    policy.save()
    with pytest.raises(ValidationError):
        change(permanent_user, reason=ChangeReason.EXPIRED)
    clock.advance(timedelta(days=1))
    with pytest.raises(ValidationError):
        change(permanent_user)
    change(permanent_user, reason=ChangeReason.EXPIRED)
    permanent_user.refresh_from_db()
    assert permanent_user.password_changed_at == clock.now()


def test_reset_change_checks_temporary_secret_and_keeps_permanent_history(
    permanent_user, clock
):
    user = permanent_user
    original_hash = user.password
    issued = issue_temporary_credential(user.pk)
    user.refresh_from_db()
    args = {"reason": ChangeReason.RESET, "credential_id": issued.credential_id}
    with pytest.raises(ValidationError):
        change(user, issued.secret, **args)
    TemporaryCredential.objects.filter(pk=issued.credential_id).update(
        consumed_at=clock.now()
    )
    with pytest.raises(ValidationError):
        change(user, OLD, **args)
    with pytest.raises(ValidationError) as error:
        change(user, issued.secret, OLD, **args)
    assert "password_reused" in {e.code for e in error.value.error_dict["new_secret"]}
    with pytest.raises(ValidationError):
        change(user, issued.secret, issued.secret[:-1] + "!", **args)
    change(user, issued.secret, **args)
    user.refresh_from_db()
    assert user.password_history.get().password_hash == original_hash
    assert user.session_version == issued.version + 1
    assert user.temporary_credentials.get().revoked_at == clock.now()


def test_first_temporary_change_starts_history_empty(user_factory, clock):
    user = user_factory()
    issued = issue_temporary_credential(user.pk)
    user.refresh_from_db()
    TemporaryCredential.objects.filter(pk=issued.credential_id).update(
        consumed_at=clock.now()
    )
    change(
        user,
        issued.secret,
        reason=ChangeReason.RESET,
        credential_id=issued.credential_id,
    )
    assert user.password_history.count() == 0


def test_history_pruned_to_five_previous_permanent_hashes(permanent_user, clock):
    secrets = [OLD]
    user = permanent_user
    for i in range(7):
        candidate = f"new completely different phrase {i}" + (
            "a" if i % 2 else "bcdefgh"
        )
        change(user, secrets[-1], candidate)
        secrets.append(candidate)
        user.refresh_from_db()
        clock.advance(timedelta(minutes=1))
    hashes = list(user.password_history.values_list("password_hash", flat=True))
    assert len(hashes) == 5
    assert all(
        check_password(secret, encoded)
        for secret, encoded in zip(reversed(secrets[-6:-1]), hashes, strict=True)
    )


def test_stale_or_blocked_context_cannot_change_password(permanent_user):
    with pytest.raises(SecurityConflict):
        change(permanent_user, expected_version=0)
    permanent_user.is_active = False
    permanent_user.save()
    with pytest.raises(SecurityConflict):
        change(permanent_user)
