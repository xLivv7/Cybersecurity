"""Explicit role rules, without inheritance from administrator privileges."""

from apps.accounts.models import User

from .models import Document


def can(user, operation, document=None):
    if (
        not user.is_active
        or user.deleted_at is not None
        or user.role not in User.Role.values
    ):
        return False
    role = user.role
    if operation == "create":
        return role in (User.Role.MANAGER, User.Role.EDITOR, User.Role.EMPLOYEE)
    if document is None:
        return False
    if document.status not in Document.Status.values:
        return False
    if operation == "read":
        return document.status == Document.Status.PUBLISHED or (
            role in (User.Role.MANAGER, User.Role.EDITOR)
            or (role == User.Role.EMPLOYEE and document.author_id == user.pk)
        )
    if operation == "edit":
        return document.status == Document.Status.DRAFT and (
            role in (User.Role.MANAGER, User.Role.EDITOR)
            or (role == User.Role.EMPLOYEE and document.author_id == user.pk)
        )
    if operation == "publish":
        return role == User.Role.MANAGER and document.status == Document.Status.DRAFT
    if operation == "withdraw":
        return (
            role == User.Role.MANAGER and document.status == Document.Status.PUBLISHED
        )
    return False
