"""Issuance invalidates old credentials atomically and keeps permanent history."""

from datetime import timedelta
from string import ascii_letters, digits

import pytest
from django.contrib.auth.hashers import check_password, make_password

from apps.security.models import PasswordHistory, TemporaryCredential
from apps.security.services import (
    issue_temporary_credential,
    verify_permanent_password,
    verify_temporary_credential,
)

pytestmark = pytest.mark.django_db


def test_issue_format_hash_deadline_and_no_logged_secret(user_factory, clock, caplog):
    user = user_factory()
    issued = issue_temporary_credential(user.pk)
    stored = TemporaryCredential.objects.get(pk=issued.credential_id)
    assert len(issued.secret) == 16
    assert set(issued.secret) <= set(ascii_letters + digits)
    assert stored.password_hash != issued.secret
    assert check_password(issued.secret, stored.password_hash)
    assert stored.issued_at == clock.now()
    assert issued.expires_at == stored.expires_at == clock.now() + timedelta(hours=4)
    assert issued.secret not in repr(issued) + caplog.text
    assert verify_temporary_credential(stored.pk, issued.secret)
    assert not verify_temporary_credential(stored.pk, "incorrect")


def test_reset_preserves_history_and_invalidates_prior_credentials(user_factory, clock):
    old = "old permanent password"
    user = user_factory(password=old, credential_mode="PERMANENT")
    history = PasswordHistory.objects.create(
        user=user, password_hash=make_password("retired password")
    )
    permanent_hash = user.password
    assert verify_permanent_password(user.pk, old)
    generations = []
    for _ in range(3):
        clock.advance(timedelta(minutes=1))
        issued = issue_temporary_credential(user.pk)
        generations.append(issued)
        user.refresh_from_db()
        assert user.credential_mode == "TEMPORARY"
        assert user.session_version == issued.version
        assert user.password == permanent_hash
        assert user.password_history.get().password_hash == history.password_hash
        assert not verify_permanent_password(user.pk, old)
        for previous in generations[:-1]:
            assert not verify_temporary_credential(
                previous.credential_id, previous.secret
            )
    assert [item.version for item in generations] == [2, 3, 4]
    assert len({item.secret for item in generations}) == 3


def test_expiration_exact_boundary(user_factory, clock):
    issued = issue_temporary_credential(user_factory().pk)
    clock.set(issued.expires_at - timedelta(microseconds=1))
    assert verify_temporary_credential(issued.credential_id, issued.secret)
    clock.set(issued.expires_at)
    assert not verify_temporary_credential(issued.credential_id, issued.secret)


def test_issuance_rolls_back_revocation_and_version_on_write_failure(
    user_factory, monkeypatch
):
    user = user_factory()
    first = issue_temporary_credential(user.pk)

    def fail(*args, **kwargs):
        raise RuntimeError("simulated storage failure")

    monkeypatch.setattr(TemporaryCredential, "save", fail)
    with pytest.raises(RuntimeError):
        issue_temporary_credential(user.pk)
    user.refresh_from_db()
    assert user.session_version == first.version
    assert TemporaryCredential.objects.count() == 1
    assert verify_temporary_credential(first.credential_id, first.secret)


def test_consumed_blocked_or_wrong_version_cannot_pass_precheck(user_factory, clock):
    user = user_factory()
    issued = issue_temporary_credential(user.pk)
    TemporaryCredential.objects.filter(pk=issued.credential_id).update(
        consumed_at=clock.now()
    )
    assert not verify_temporary_credential(issued.credential_id, issued.secret)
    newer = issue_temporary_credential(user.pk)
    user.refresh_from_db()
    user.is_active = False
    user.save()
    assert not verify_temporary_credential(newer.credential_id, newer.secret)
    user.is_active = True
    user.session_version += 1
    user.save()
    assert not verify_temporary_credential(newer.credential_id, newer.secret)
