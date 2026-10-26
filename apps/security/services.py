"""Domain operations for password credentials, independent of HTTP sessions."""

import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from functools import wraps

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import OperationalError, transaction
from django.db.models import F
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from .constants import (
    PASSWORD_HISTORY_SIZE,
    TEMPORARY_PASSWORD_LENGTH,
    TEMPORARY_PASSWORD_LIFETIME,
)
from .models import PasswordHistory, TemporaryCredential
from .selectors import get_security_settings
from .validators import validate_permanent_password


class SecurityConflict(ValidationError):
    def __init__(self):
        super().__init__(
            "Stan bezpieczeństwa zmienił się. Ponów operację.", code="security_conflict"
        )


def database_operation(operation):
    """Translate lock/deadlock failures after leaving the atomic block."""

    @wraps(operation)
    @sensitive_variables()
    def guarded(*args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except OperationalError:
            raise SecurityConflict() from None

    return guarded


def _account_state(user):
    return (
        user.password,
        user.credential_mode,
        user.session_version,
        user.password_changed_at,
        user.is_active,
        user.deleted_at,
    )


def _credential_state(credential):
    if credential is None:
        return None
    return (
        credential.user_id,
        credential.password_hash,
        credential.credential_version,
        credential.issued_at,
        credential.expires_at,
        credential.consumed_at,
        credential.revoked_at,
    )


def _policy_state(policy):
    return (
        policy.levenshtein_enabled,
        policy.password_max_age_days,
        policy.idle_timeout_minutes,
        policy.updated_at,
    )


def _history_state(user):
    return list(
        user.password_history.values_list("pk", "password_hash", "replaced_at")[
            :PASSWORD_HISTORY_SIZE
        ]
    )


class ChangeReason(StrEnum):
    VOLUNTARY = "VOLUNTARY"
    INITIAL = "INITIAL"
    EXPIRED = "EXPIRED"
    RESET = "RESET"


@dataclass(frozen=True)
class PasswordChangeResult:
    user_id: int
    version: int


def _check_change_context(user, reason, expected_version, policy, credential, now):
    if (
        not user.is_active
        or user.deleted_at is not None
        or user.session_version != expected_version
    ):
        raise SecurityConflict()
    expired = (
        policy.password_max_age_days > 0
        and user.password_changed_at is not None
        and (now - user.password_changed_at) // timedelta(days=1)
        >= policy.password_max_age_days
    )
    if reason == ChangeReason.RESET:
        valid = (
            user.credential_mode == user.CredentialMode.TEMPORARY
            and credential is not None
            and credential.user_id == user.pk
            and credential.credential_version == expected_version
            and credential.consumed_at is not None
            and credential.consumed_at <= now
            and credential.revoked_at is None
            and credential.issued_at <= now < credential.expires_at
        )
    elif reason == ChangeReason.INITIAL:
        valid = user.credential_mode == user.CredentialMode.INITIAL
    elif reason in (ChangeReason.VOLUNTARY, ChangeReason.EXPIRED):
        valid = user.credential_mode == user.CredentialMode.PERMANENT and (
            expired if reason == ChangeReason.EXPIRED else not expired
        )
    else:
        valid = False
    if not valid:
        raise ValidationError(
            "Nieprawidłowy kontekst zmiany hasła.", code="invalid_context"
        )


@database_operation
@sensitive_variables()
def change_password(
    user_id,
    old_secret,
    new_secret,
    confirmation,
    *,
    reason,
    expected_version,
    credential_id=None,
):
    """Caller supplies a trusted session context; success invalidates its version.

    For RESET, credential_id must come from the limited context established by
    consumption, never directly from an untrusted form field.
    """
    User = get_user_model()
    user = User.objects.get(pk=user_id)
    policy = get_security_settings()
    credential = (
        TemporaryCredential.objects.get(pk=credential_id)
        if reason == ChangeReason.RESET and credential_id is not None
        else None
    )
    _check_change_context(
        user, reason, expected_version, policy, credential, timezone.now()
    )
    history_before_validation = _history_state(user)
    validate_permanent_password(
        user,
        old_secret,
        new_secret,
        confirmation,
        source_hash=credential.password_hash if credential else None,
        policy=policy,
    )
    encoded = make_password(new_secret)
    with transaction.atomic():
        current = User.objects.get(pk=user_id)
        if _account_state(current) != _account_state(user):
            raise SecurityConflict()
        current_credential = (
            TemporaryCredential.objects.get(pk=credential.pk) if credential else None
        )
        if (
            _credential_state(current_credential) != _credential_state(credential)
            or _history_state(current) != history_before_validation
            or _policy_state(get_security_settings()) != _policy_state(policy)
        ):
            raise SecurityConflict()
        now = timezone.now()
        _check_change_context(
            current, reason, expected_version, policy, current_credential, now
        )
        changed = User.objects.filter(
            pk=user_id, session_version=expected_version
        ).update(
            password=encoded,
            password_changed_at=now,
            credential_mode=User.CredentialMode.PERMANENT,
            session_version=F("session_version") + 1,
        )
        if changed != 1:
            raise SecurityConflict()
        if user.has_usable_password() and user.password_changed_at is not None:
            PasswordHistory.objects.create(
                user=user, password_hash=user.password, replaced_at=now
            )
        retired_ids = list(
            PasswordHistory.objects.filter(user=user).values_list("pk", flat=True)[
                PASSWORD_HISTORY_SIZE:
            ]
        )
        PasswordHistory.objects.filter(pk__in=retired_ids).delete()
        TemporaryCredential.objects.filter(user=user, revoked_at__isnull=True).update(
            revoked_at=now
        )
    return PasswordChangeResult(user_id, expected_version + 1)


@dataclass(frozen=True)
class IssuedCredential:
    credential_id: int
    user_id: int
    version: int
    expires_at: datetime
    secret: str = field(repr=False)


@database_operation
@sensitive_variables()
def issue_temporary_credential(user_id):
    """Return the secret once; persist only its salted hash, preserving history."""
    alphabet = string.ascii_letters + string.digits
    secret = "".join(secrets.choice(alphabet) for _ in range(TEMPORARY_PASSWORD_LENGTH))
    encoded = make_password(secret)
    User = get_user_model()
    with transaction.atomic():
        user = User.objects.get(pk=user_id)
        if user.deleted_at is not None:
            raise ValidationError(
                "Nie można resetować usuniętego konta.", code="inactive_account"
            )
        now = timezone.now()
        TemporaryCredential.objects.filter(user=user, revoked_at__isnull=True).update(
            revoked_at=now
        )
        changed = User.objects.filter(
            pk=user.pk, session_version=user.session_version
        ).update(
            credential_mode=User.CredentialMode.TEMPORARY,
            session_version=F("session_version") + 1,
        )
        if changed != 1:
            raise SecurityConflict()
        user.refresh_from_db(fields=["session_version"])
        credential = TemporaryCredential.objects.create(
            user=user,
            password_hash=encoded,
            issued_at=now,
            expires_at=now + TEMPORARY_PASSWORD_LIFETIME,
            credential_version=user.session_version,
        )
    return IssuedCredential(
        credential.pk, user.pk, user.session_version, credential.expires_at, secret
    )


@dataclass(frozen=True)
class ConsumedCredential:
    credential_id: int
    user_id: int
    version: int
    expires_at: datetime


def _eligible_temporary_credential(credential, now):
    user = credential.user
    return (
        user.is_active
        and user.deleted_at is None
        and user.credential_mode == user.CredentialMode.TEMPORARY
        and user.session_version == credential.credential_version
        and credential.issued_at <= now < credential.expires_at
        and credential.consumed_at is None
        and credential.revoked_at is None
    )


@database_operation
@sensitive_variables()
def consume_temporary_credential(credential_id, secret):
    """Only a successful conditional write may establish a limited context."""
    try:
        credential = TemporaryCredential.objects.select_related("user").get(
            pk=credential_id
        )
    except TemporaryCredential.DoesNotExist:
        raise SecurityConflict() from None
    if not check_password(secret, credential.password_hash):
        raise ValidationError("Login lub hasło niepoprawne", code="invalid_credentials")
    if not _eligible_temporary_credential(credential, timezone.now()):
        raise SecurityConflict()
    with transaction.atomic():
        current = TemporaryCredential.objects.select_related("user").get(
            pk=credential_id
        )
        now = timezone.now()
        if (
            _credential_state(current) != _credential_state(credential)
            or _account_state(current.user) != _account_state(credential.user)
            or not _eligible_temporary_credential(current, now)
        ):
            raise SecurityConflict()
        changed = TemporaryCredential.objects.filter(
            pk=credential_id,
            password_hash=credential.password_hash,
            credential_version=credential.credential_version,
            user__session_version=credential.credential_version,
            user__credential_mode=current.user.CredentialMode.TEMPORARY,
            user__is_active=True,
            user__deleted_at__isnull=True,
            consumed_at__isnull=True,
            revoked_at__isnull=True,
            issued_at__lte=now,
            expires_at__gt=now,
        ).update(consumed_at=now)
        if changed != 1:
            raise SecurityConflict()
    return ConsumedCredential(
        credential.pk,
        credential.user_id,
        credential.credential_version,
        credential.expires_at,
    )


@sensitive_variables("secret")
def verify_permanent_password(user_id, secret):
    """Check current permanent credentials; expiry/scope is decided in E3."""
    User = get_user_model()
    user = User.objects.get(pk=user_id)
    return (
        user.is_active
        and user.deleted_at is None
        and user.credential_mode == User.CredentialMode.PERMANENT
        and check_password(secret, user.password)
        and User.objects.filter(
            pk=user_id,
            password=user.password,
            session_version=user.session_version,
            is_active=True,
            deleted_at__isnull=True,
            credential_mode=User.CredentialMode.PERMANENT,
        ).exists()
    )


@sensitive_variables("secret")
def verify_temporary_credential(credential_id, secret):
    """Read-only precheck; granting a limited context requires T011 consumption."""
    credential = TemporaryCredential.objects.select_related("user").get(
        pk=credential_id
    )
    matches = check_password(secret, credential.password_hash)
    now = timezone.now()
    user = credential.user
    return (
        matches
        and user.is_active
        and user.deleted_at is None
        and user.credential_mode == user.CredentialMode.TEMPORARY
        and user.session_version == credential.credential_version
        and credential.issued_at <= now < credential.expires_at
        and credential.consumed_at is None
        and credential.revoked_at is None
    )
