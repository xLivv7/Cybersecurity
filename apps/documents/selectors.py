from django.db.models import Q

from apps.accounts.models import User

from .models import Document


def visible_documents(user):
    documents = Document.objects.select_related("author")
    if (
        not user.is_active
        or user.deleted_at is not None
        or user.role not in User.Role.values
    ):
        return documents.none()
    if user.role in (User.Role.MANAGER, User.Role.EDITOR):
        return documents
    if user.role == User.Role.EMPLOYEE:
        return documents.filter(Q(status=Document.Status.PUBLISHED) | Q(author=user))
    return documents.filter(status=Document.Status.PUBLISHED)
