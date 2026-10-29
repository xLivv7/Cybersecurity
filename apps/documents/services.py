"""Reload both actor and document inside short transactions before mutation."""

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.accounts.backends import password_expired
from apps.accounts.models import User
from apps.security.selectors import get_security_settings
from apps.security.services import database_operation

from .models import Document
from .policies import can


def current_actor(actor):
    user = User.objects.get(pk=actor.pk)
    if (
        not user.is_active
        or user.deleted_at is not None
        or user.session_version != actor.session_version
        or user.credential_mode != User.CredentialMode.PERMANENT
        or password_expired(user, get_security_settings(), timezone.now())
    ):
        raise PermissionDenied
    return user


@database_operation
def create_document(actor, *, title, body):
    with transaction.atomic():
        actor = current_actor(actor)
        if not can(actor, "create"):
            raise PermissionDenied
        return Document.objects.create(author=actor, title=title, body=body)


@database_operation
def edit_document(actor, document_id, *, title, body):
    with transaction.atomic():
        actor = current_actor(actor)
        document = Document.objects.get(pk=document_id)
        if not can(actor, "edit", document):
            raise PermissionDenied
        document.title, document.body = title, body
        document.save()
        return document


@database_operation
def transition_document(actor, document_id, operation):
    with transaction.atomic():
        actor = current_actor(actor)
        document = Document.objects.get(pk=document_id)
        if operation not in ("publish", "withdraw") or not can(
            actor, operation, document
        ):
            raise PermissionDenied
        document.status = (
            Document.Status.PUBLISHED
            if operation == "publish"
            else Document.Status.DRAFT
        )
        document.save()
        return document
