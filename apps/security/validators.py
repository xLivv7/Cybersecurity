"""Validation of encoded secrets without including them in error messages."""

from argon2 import Type, extract_parameters
from argon2.exceptions import InvalidHashError
from django.core.exceptions import ValidationError


def validate_password_hash(value):
    try:
        if not isinstance(value, str) or not value.startswith("argon2$argon2id$"):
            raise ValueError
        parameters = extract_parameters(value.removeprefix("argon2"))
        if (
            parameters.type != Type.ID
            or not parameters.salt_len
            or not parameters.hash_len
        ):
            raise ValueError
    except (ValueError, InvalidHashError):
        raise ValidationError(
            "Wymagany jest hash Argon2id z solą.", code="invalid_password_hash"
        ) from None
