"""Credential classification is distinct from granting a Django login."""

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from apps.security.models import TemporaryCredential
from apps.security.selectors import get_security_settings
from apps.security.services import ChangeReason

LOGIN_ERROR = "Login lub hasło niepoprawne"
BACKEND_PATH = "apps.accounts.backends.CredentialBackend"


@dataclass(frozen=True)
class LoginResult:
    user_id: int
    version: int
    reason: str | None = None
    credential_id: int | None = None


def password_expired(user, policy, now):
    from datetime import timedelta

    return (
        policy.password_max_age_days > 0
        and user.password_changed_at is not None
        and (now - user.password_changed_at) // timedelta(days=1)
        >= policy.password_max_age_days
    )


@sensitive_variables()
def authenticate_login(login, password):
    User = get_user_model()
    user = User.objects.filter(login_key=login.strip().casefold()).first()
    if user is None:
        make_password(password)
        return None
    credential = None
    if user.credential_mode == User.CredentialMode.TEMPORARY:
        credential = TemporaryCredential.objects.filter(
            user=user, credential_version=user.session_version
        ).first()
        if credential is None:
            make_password(password)
            return None
        encoded = credential.password_hash
    else:
        encoded = user.password
    if not check_password(password, encoded):
        return None
    if not User.objects.filter(
        pk=user.pk,
        password=user.password,
        session_version=user.session_version,
        credential_mode=user.credential_mode,
        is_active=True,
        deleted_at__isnull=True,
    ).exists():
        return None
    now = timezone.now()
    if credential is not None:
        if not TemporaryCredential.objects.filter(
            pk=credential.pk,
            password_hash=encoded,
            consumed_at__isnull=True,
            revoked_at__isnull=True,
            issued_at__lte=now,
            expires_at__gt=now,
        ).exists():
            return None
        return LoginResult(
            user.pk, user.session_version, ChangeReason.RESET, credential.pk
        )
    if user.credential_mode == User.CredentialMode.INITIAL:
        return LoginResult(user.pk, user.session_version, ChangeReason.INITIAL)
    if user.credential_mode != User.CredentialMode.PERMANENT:
        return None
    reason = (
        ChangeReason.EXPIRED
        if password_expired(user, get_security_settings(), now)
        else None
    )
    return LoginResult(user.pk, user.session_version, reason)


class CredentialBackend(BaseBackend):
    @sensitive_variables()
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        result = authenticate_login(username, password)
        if result is None or result.reason is not None:
            return None
        return (
            get_user_model()
            .objects.filter(
                pk=result.user_id,
                session_version=result.version,
                credential_mode="PERMANENT",
                is_active=True,
                deleted_at__isnull=True,
            )
            .first()
        )

    def get_user(self, user_id):
        return (
            get_user_model()
            .objects.filter(
                pk=user_id,
                is_active=True,
                deleted_at__isnull=True,
                credential_mode="PERMANENT",
            )
            .first()
        )
