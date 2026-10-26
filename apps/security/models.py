"""A single database-backed security policy, read without a persistent cache."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Cast
from django.utils import timezone

from .fields import PasswordHashField, PolicyIntegerField


def current_time():
    """Resolve the clock at call time so tests can control timestamp defaults."""
    return timezone.now()


class SecuritySettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    levenshtein_enabled = models.BooleanField("reguła Levenshteina", default=True)
    password_max_age_days = PolicyIntegerField(
        "ważność hasła w dniach", default=0, validators=[MinValueValidator(0)]
    )
    idle_timeout_minutes = PolicyIntegerField(
        "limit bezczynności w minutach", default=15, validators=[MinValueValidator(1)]
    )
    updated_at = models.DateTimeField("ostatnia zmiana", auto_now=True)

    class Meta:
        verbose_name = "ustawienia bezpieczeństwa"
        verbose_name_plural = "ustawienia bezpieczeństwa"
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name="security_single_settings"),
            models.CheckConstraint(
                condition=Q(password_max_age_days__gte=0)
                & Q(
                    password_max_age_days=Cast(
                        F("password_max_age_days"), models.IntegerField()
                    )
                ),
                name="security_valid_password_age",
            ),
            models.CheckConstraint(
                condition=Q(idle_timeout_minutes__gte=1)
                & Q(
                    idle_timeout_minutes=Cast(
                        F("idle_timeout_minutes"), models.IntegerField()
                    )
                ),
                name="security_valid_idle_timeout",
            ),
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        # Partial saves must still record when the policy was changed.
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"updated_at"}
        return super().save(*args, **kwargs)


class PasswordHistory(models.Model):
    """Retired permanent passwords; reset credentials never enter this table."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="password_history",
        verbose_name="użytkownik",
    )
    password_hash = PasswordHashField("hash hasła stałego", max_length=128)
    replaced_at = models.DateTimeField("czas zastąpienia", default=current_time)

    class Meta:
        verbose_name = "historia hasła"
        verbose_name_plural = "historia haseł"
        ordering = ["-replaced_at", "-pk"]

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class TemporaryCredential(models.Model):
    """A reset generation with its own hash and lifecycle timestamps."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="temporary_credentials",
        verbose_name="użytkownik",
    )
    password_hash = PasswordHashField("hash hasła tymczasowego", max_length=128)
    issued_at = models.DateTimeField("czas wydania", default=current_time)
    expires_at = models.DateTimeField("czas wygaśnięcia")
    consumed_at = models.DateTimeField("czas zużycia", null=True, blank=True)
    revoked_at = models.DateTimeField("czas unieważnienia", null=True, blank=True)
    credential_version = models.PositiveBigIntegerField("wersja poświadczenia")

    class Meta:
        verbose_name = "poświadczenie tymczasowe"
        verbose_name_plural = "poświadczenia tymczasowe"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "credential_version"],
                name="security_unique_credential_version",
            ),
            models.CheckConstraint(
                condition=Q(credential_version__gte=1),
                name="security_positive_credential_version",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("issued_at")),
                name="security_credential_expires_after_issue",
            ),
            models.CheckConstraint(
                condition=Q(consumed_at__isnull=True)
                | (
                    Q(consumed_at__gte=F("issued_at"))
                    & Q(consumed_at__lt=F("expires_at"))
                ),
                name="security_credential_consumed_in_time",
            ),
            models.CheckConstraint(
                condition=Q(revoked_at__isnull=True)
                | Q(revoked_at__gte=F("issued_at")),
                name="security_credential_revoked_after_issue",
            ),
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
