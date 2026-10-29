"""Hash outside the write lock; decide limits and grant access atomically."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from apps.accounts.backends import authenticate_login

from .constants import LOGIN_LOCK_SECONDS
from .login_keys import login_identity_key
from .models import LoginAttemptState, SecurityEvent, TemporaryCredential
from .selectors import get_security_settings
from .services import (
    SecurityConflict,
    _account_state,
    _credential_state,
    database_operation,
)
from .sessions import start_session


@dataclass(frozen=True)
class LoginAttempt:
    context: dict | None = field(default=None, repr=False)
    blocked_until: datetime | None = None


def get_login_block(login):
    """Read-only: checking the deadline never creates or renews state."""
    return (
        LoginAttemptState.objects.filter(
            identity_key=login_identity_key(login), blocked_until__gt=timezone.now()
        )
        .values_list("blocked_until", flat=True)
        .first()
    )


@sensitive_variables()
def _snapshot(login):
    user = get_user_model().objects.filter(login_key=login.strip().casefold()).first()
    credential = None
    if user is not None and user.credential_mode == "TEMPORARY":
        credential = (
            TemporaryCredential.objects.select_related("user")
            .filter(user=user, credential_version=user.session_version)
            .first()
        )
    signature = (
        (user.pk, _account_state(user)) if user is not None else None,
        _credential_state(credential),
    )
    return signature, credential


def _event(category, key):
    SecurityEvent.objects.create(category=category, identity_key=key)


def _lock(state, now):
    state.blocked_until = now + timedelta(seconds=LOGIN_LOCK_SECONDS)
    _event(SecurityEvent.Category.ACCOUNT_LOCKED, state.identity_key)


@database_operation
@sensitive_variables()
def attempt_login(request, login, password):
    blocked_until = get_login_block(login)
    if blocked_until is not None:
        return LoginAttempt(blocked_until=blocked_until)
    signature, credential = _snapshot(login)
    result = authenticate_login(login, password)
    key = login_identity_key(login)
    with transaction.atomic():
        state, _ = LoginAttemptState.objects.select_for_update().get_or_create(
            identity_key=key
        )
        now = timezone.now()
        if state.blocked_until is not None:
            if now < state.blocked_until:
                return LoginAttempt(blocked_until=state.blocked_until)
            state.blocked_until = None
            state.failure_count = 0
        limit = get_security_settings().login_failure_limit
        # Lowering the policy cannot be bypassed by a concurrent correct password.
        if state.failure_count >= limit:
            _lock(state, now)
        else:
            if _snapshot(login)[0] != signature:
                raise SecurityConflict()
            if result is None:
                state.failure_count += 1
                _event(SecurityEvent.Category.CREDENTIAL_FAILURE, key)
                if state.failure_count >= limit:
                    _lock(state, now)
            else:
                state.failure_count = 0
        state.version += 1
        state.save()
        if state.blocked_until is not None or result is None:
            return LoginAttempt(blocked_until=state.blocked_until)
        context = start_session(
            request, result, password, _verified_credential=credential
        )
        # Persist the granted context in the same transaction as the decision.
        request.session.save()
        return LoginAttempt(context=context)
