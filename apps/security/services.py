"""Domain operations for password credentials, independent of HTTP sessions."""

import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from .constants import TEMPORARY_PASSWORD_LENGTH, TEMPORARY_PASSWORD_LIFETIME
from .models import TemporaryCredential


@dataclass(frozen=True)
class IssuedCredential:
    credential_id: int
    user_id: int
    version: int
    expires_at: datetime
    secret: str = field(repr=False)


@sensitive_variables("secret", "encoded")
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
        User.objects.filter(pk=user.pk).update(
            credential_mode=User.CredentialMode.TEMPORARY,
            session_version=F("session_version") + 1,
        )
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
