"""Server-side full and limited contexts; no plaintext credentials in sessions."""

from datetime import datetime
from functools import wraps

from django.contrib import auth
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from apps.accounts.backends import BACKEND_PATH, password_expired

from .models import TemporaryCredential
from .selectors import get_security_settings
from .services import ChangeReason, SecurityConflict, consume_temporary_credential

CONTEXT_KEY = "security_context"


@sensitive_variables()
def start_session(request, result, password):
    User = get_user_model()
    user = User.objects.get(pk=result.user_id)
    if (
        not user.is_active
        or user.deleted_at is not None
        or user.session_version != result.version
    ):
        raise SecurityConflict()
    now = timezone.now()
    reason, expires_at = result.reason, None
    if reason == ChangeReason.RESET:
        consumed = consume_temporary_credential(result.credential_id, password)
        if consumed.user_id != user.pk or consumed.version != result.version:
            raise SecurityConflict()
        expires_at = consumed.expires_at.isoformat()
    elif reason == ChangeReason.INITIAL:
        if user.credential_mode != User.CredentialMode.INITIAL:
            raise SecurityConflict()
    elif user.credential_mode == User.CredentialMode.PERMANENT:
        reason = (
            ChangeReason.EXPIRED
            if password_expired(user, get_security_settings(), now)
            else None
        )
    else:
        raise ValidationError("Nieprawidłowy kontekst logowania.")
    auth.logout(request)
    request.session.cycle_key()
    if reason is None:
        auth.login(request, user, backend=BACKEND_PATH)
    request.session[CONTEXT_KEY] = {
        "scope": "full" if reason is None else "limited",
        "user_id": user.pk,
        "version": result.version,
        "reason": reason,
        "credential_id": result.credential_id,
        "expires_at": expires_at,
        "last_activity": timezone.now().isoformat(),
    }
    return request.session[CONTEXT_KEY]


def get_access(request):
    """Validate account identity and version on every protected view."""
    data = request.session.get(CONTEXT_KEY)
    if data is None:
        return None
    try:
        if (
            not isinstance(data, dict)
            or type(data["user_id"]) is not int
            or type(data["version"]) is not int
        ):
            raise ValueError
        user = get_user_model().objects.get(
            pk=data["user_id"], is_active=True, deleted_at__isnull=True
        )
        if user.session_version != data["version"]:
            raise ValueError
        if data["scope"] == "full":
            if (
                data["reason"] is not None
                or not request.user.is_authenticated
                or request.user.pk != user.pk
                or user.credential_mode != user.CredentialMode.PERMANENT
            ):
                raise ValueError
        elif data["scope"] == "limited":
            if request.user.is_authenticated:
                raise ValueError
            if data["reason"] == ChangeReason.RESET:
                expires = datetime.fromisoformat(data["expires_at"])
                if timezone.is_naive(expires) or timezone.now() >= expires:
                    raise ValueError
                if (
                    not TemporaryCredential.objects.filter(
                        pk=data["credential_id"],
                        user=user,
                        credential_version=data["version"],
                        consumed_at__isnull=False,
                        revoked_at__isnull=True,
                        expires_at=expires,
                        issued_at__lte=timezone.now(),
                    ).exists()
                    or user.credential_mode != user.CredentialMode.TEMPORARY
                ):
                    raise ValueError
            elif data["reason"] == ChangeReason.INITIAL:
                if user.credential_mode != user.CredentialMode.INITIAL:
                    raise ValueError
            elif data["reason"] == ChangeReason.EXPIRED:
                if user.credential_mode != user.CredentialMode.PERMANENT:
                    raise ValueError
            else:
                raise ValueError
        else:
            raise ValueError
        return user, data
    except (KeyError, TypeError, ValueError, get_user_model().DoesNotExist):
        auth.logout(request)
        return None


def access_required(scope):
    def decorate(view):
        @wraps(view)
        def guarded(request, *args, **kwargs):
            access = get_access(request)
            if access is None:
                return redirect("accounts:login")
            user, data = access
            if data["scope"] != scope:
                return redirect(
                    "security:password_required"
                    if data["scope"] == "limited"
                    else "home"
                )
            request.access_user, request.access_context = user, data
            return view(request, *args, **kwargs)

        return guarded

    return decorate
