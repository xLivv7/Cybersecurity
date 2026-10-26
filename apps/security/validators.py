"""Validation of encoded secrets without including them in error messages."""

from argon2 import Type, extract_parameters
from argon2.exceptions import InvalidHashError
from django.core.exceptions import ValidationError


def validate_permanent_password(
    user, old_secret, new_secret, confirmation, *, source_hash=None, policy=None
):
    """Validate without writing or normalizing any password or user data.

    source_hash selects the temporary secret during a reset; reuse checks still
    include the last permanent password and its five retired predecessors.
    """
    from django.contrib.auth.hashers import check_password
    from django.contrib.auth.password_validation import validate_password

    from .constants import MIN_LEVENSHTEIN_DISTANCE, PASSWORD_HISTORY_SIZE
    from .passwords import levenshtein_distance
    from .selectors import get_security_settings

    if not all(
        isinstance(value, str) for value in (old_secret, new_secret, confirmation)
    ):
        raise ValidationError("Hasła muszą być tekstem.", code="invalid_secret")
    errors = {}
    if not check_password(
        old_secret, user.password if source_hash is None else source_hash
    ):
        errors["old_secret"] = ValidationError(
            "Dotychczasowe hasło jest niepoprawne.", code="invalid_old_secret"
        )
    if new_secret != confirmation:
        errors["confirmation"] = ValidationError(
            "Potwierdzenie hasła musi być identyczne.", code="password_mismatch"
        )
    try:
        validate_password(new_secret, user=user)
    except ValidationError as error:
        errors["new_secret"] = error.error_list
    policy = policy if policy is not None else get_security_settings()
    if policy.levenshtein_enabled and (
        levenshtein_distance(old_secret, new_secret) < MIN_LEVENSHTEIN_DISTANCE
    ):
        errors.setdefault("new_secret", []).append(
            ValidationError(
                "Nowe hasło musi różnić się od dotychczasowego o co najmniej 4 operacje.",
                code="password_too_similar",
            )
        )
    history = user.password_history.values_list("password_hash", flat=True)[
        :PASSWORD_HISTORY_SIZE
    ]
    if any(
        check_password(new_secret, encoded) for encoded in [user.password, *history]
    ):
        errors.setdefault("new_secret", []).append(
            ValidationError(
                "Nie można ponownie użyć bieżącego ani pięciu poprzednich haseł.",
                code="password_reused",
            )
        )
    if errors:
        raise ValidationError(errors)


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
