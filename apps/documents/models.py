"""Plain-text documents retain authorship after logical account deletion."""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


def current_time():
    return timezone.now()


class Document(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Szkic"
        PUBLISHED = "PUBLISHED", "Opublikowany"

    title = models.CharField("Tytuł", max_length=200)
    body = models.TextField("Treść")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents",
        verbose_name="Autor",
    )
    status = models.CharField(
        "Stan", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    created_at = models.DateTimeField("Utworzono", default=current_time)
    updated_at = models.DateTimeField("Zmieniono", auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["DRAFT", "PUBLISHED"]),
                name="document_valid_status",
            )
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
