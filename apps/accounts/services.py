"""Account management checks the actor and updates session versions atomically."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.security.services import (
    database_operation,
    issue_temporary_credential,
    prepare_temporary_credential,
)

from .models import User


def require_administrator(actor):
    if not User.objects.filter(
        pk=actor.pk,
        role=User.Role.ADMINISTRATOR,
        is_active=True,
        deleted_at__isnull=True,
        session_version=actor.session_version,
    ).exists():
        raise PermissionDenied


@database_operation
def create_account(
    actor, *, username, first_name="", last_name="", role, _prepared=None
):
    require_administrator(actor)
    if role not in User.Role.values or role == User.Role.ADMINISTRATOR:
        raise ValidationError({"role": "Wybierz rolę biznesową."})
    prepared = _prepared if _prepared is not None else prepare_temporary_credential()
    with transaction.atomic():
        require_administrator(actor)
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        issued = issue_temporary_credential(user.pk, _prepared=prepared)
        user.refresh_from_db()
    return user, issued


@database_operation
def edit_account(actor, user_id, *, first_name, last_name, role):
    with transaction.atomic():
        require_administrator(actor)
        user = User.objects.get(pk=user_id, deleted_at__isnull=True)
        if role != user.role:
            user.session_version += 1
        user.first_name, user.last_name, user.role = first_name, last_name, role
        user.save()
        return user


@database_operation
def account_action(actor, user_id, action, *, _prepared=None):
    require_administrator(actor)
    prepared = (
        (_prepared if _prepared is not None else prepare_temporary_credential())
        if action == "reset"
        else None
    )
    with transaction.atomic():
        require_administrator(actor)
        user = User.objects.get(pk=user_id, deleted_at__isnull=True)
        if user.login_key == "admin":
            raise ValidationError("Ta operacja nie jest dostępna dla konta ADMIN.")
        if action == "reset":
            return issue_temporary_credential(user.pk, _prepared=prepared)
        if action == "block":
            user.is_active = False
        elif action == "unblock":
            user.is_active = True
        elif action == "delete":
            user.is_active = False
            user.deleted_at = timezone.now()
        else:
            raise ValidationError("Nieznana operacja.")
        user.session_version += 1
        user.save()
        return None
