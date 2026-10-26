"""Password policy uses real hashes and preserves exact password text."""

import pytest
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError

from apps.security.models import PasswordHistory
from apps.security.validators import validate_permanent_password

pytestmark = pytest.mark.django_db

OLD = "previous long passphrase"
NEW = "different long passphrase"


@pytest.fixture
def password_user(user_factory):
    return user_factory(password=OLD)


def error_codes(error, field):
    return {item.code for item in error.value.error_dict[field]}


@pytest.mark.parametrize(
    "candidate, accepted", [("abcdefghijklm", False), ("abcdefghijklmn", True)]
)
def test_minimum_length_boundary(password_user, candidate, accepted):
    if accepted:
        validate_permanent_password(password_user, OLD, candidate, candidate)
    else:
        with pytest.raises(ValidationError) as error:
            validate_permanent_password(password_user, OLD, candidate, candidate)
        assert "password_too_short" in error_codes(error, "new_secret")


def test_confirmation_and_old_secret_must_match_exactly(password_user):
    with pytest.raises(ValidationError) as error:
        validate_permanent_password(password_user, OLD.upper(), NEW, NEW.upper())
    assert error_codes(error, "old_secret") == {"invalid_old_secret"}
    assert error_codes(error, "confirmation") == {"password_mismatch"}


def test_common_password_rejected_without_character_class_rules(password_user):
    with pytest.raises(ValidationError) as error:
        validate_permanent_password(password_user, OLD, "password", "password")
    assert "password_too_common" in error_codes(error, "new_secret")
    validate_permanent_password(password_user, OLD, NEW, NEW)


def test_current_permanent_password_is_rejected_even_in_temporary_mode(password_user):
    password_user.credential_mode = password_user.CredentialMode.TEMPORARY
    password_user.save()
    temporary = "A1b2C3d4E5f6G7h8"
    with pytest.raises(ValidationError) as error:
        validate_permanent_password(
            password_user, temporary, OLD, OLD, source_hash=make_password(temporary)
        )
    assert "password_reused" in error_codes(error, "new_secret")


def test_five_newest_history_entries_are_checked(password_user):
    candidates = [f"historical passphrase number {i}" for i in range(6)]
    for candidate in candidates:
        PasswordHistory.objects.create(
            user=password_user, password_hash=make_password(candidate)
        )
    for candidate in candidates[1:]:
        with pytest.raises(ValidationError) as error:
            validate_permanent_password(password_user, OLD, candidate, candidate)
        assert "password_reused" in error_codes(error, "new_secret")
    validate_permanent_password(password_user, OLD, candidates[0], candidates[0])


def test_whitespace_and_unicode_are_not_normalized(user_factory):
    old = "  previous passphrase  "
    user = user_factory(password=old)
    candidate = "  nowe hasło żółwia  "
    validate_permanent_password(user, old, candidate, candidate)
    with pytest.raises(ValidationError) as error:
        validate_permanent_password(user, old.strip(), candidate, candidate.strip())
    assert "old_secret" in error.value.message_dict
    assert "confirmation" in error.value.message_dict


def test_validation_does_not_modify_hash_history_or_timestamp(password_user):
    before = (password_user.password, password_user.password_changed_at)
    validate_permanent_password(password_user, OLD, NEW, NEW)
    with pytest.raises(ValidationError):
        validate_permanent_password(password_user, "wrong", NEW, NEW)
    password_user.refresh_from_db()
    assert (password_user.password, password_user.password_changed_at) == before
    assert password_user.password_history.count() == 0
