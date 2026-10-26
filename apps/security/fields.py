"""Integer settings must not silently truncate fractional input."""

from django.core.exceptions import ValidationError
from django.db import models

from .validators import validate_password_hash


class PasswordHashField(models.CharField):
    """Require an encoded Argon2id hash even for ordinary bulk ORM writes."""

    default_validators = [validate_password_hash]

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        validate_password_hash(value)
        return value


class PolicyIntegerField(models.IntegerField):
    def to_python(self, value):
        converted = super().to_python(value)
        if isinstance(value, bool) or (
            value is not None and not isinstance(value, str) and value != converted
        ):
            raise ValidationError(
                "Podaj liczbę całkowitą.", code="invalid", params={"value": value}
            )
        return converted

    def get_prep_value(self, value):
        # QuerySet.update and bulk writes also pass through this conversion.
        return self.to_python(value)
