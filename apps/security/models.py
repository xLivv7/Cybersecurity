"""A single database-backed security policy, read without a persistent cache."""

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Cast

from .fields import PolicyIntegerField


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
