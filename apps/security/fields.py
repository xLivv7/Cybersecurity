"""Integer settings must not silently truncate fractional input."""

from django.core.exceptions import ValidationError
from django.db import models


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
