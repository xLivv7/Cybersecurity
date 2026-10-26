"""Policy defaults, strict validation, database constraints and fresh reads."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import Value

from apps.security.constants import (
    MIN_LEVENSHTEIN_DISTANCE,
    MIN_PASSWORD_LENGTH,
    PASSWORD_HISTORY_SIZE,
    TEMPORARY_PASSWORD_LENGTH,
    TEMPORARY_PASSWORD_LIFETIME,
)
from apps.security.models import SecuritySettings
from apps.security.selectors import get_security_settings

pytestmark = pytest.mark.django_db


def test_migrations_seed_exactly_one_policy_with_defaults():
    assert SecuritySettings.objects.count() == 1
    policy = get_security_settings()
    assert policy.pk == 1
    assert policy.levenshtein_enabled is True
    assert policy.password_max_age_days == 0
    assert policy.idle_timeout_minutes == 15
    assert policy.updated_at.utcoffset() == timedelta(0)


def test_fixed_policy_constants():
    assert MIN_PASSWORD_LENGTH == 14
    assert MIN_LEVENSHTEIN_DISTANCE == 4
    assert PASSWORD_HISTORY_SIZE == 5
    assert TEMPORARY_PASSWORD_LENGTH == 16
    assert TEMPORARY_PASSWORD_LIFETIME == timedelta(hours=4)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("password_max_age_days", -1),
        ("idle_timeout_minutes", -1),
        ("idle_timeout_minutes", 0),
        *[
            (field, value)
            for field in ("password_max_age_days", "idle_timeout_minutes")
            for value in (1.5, Decimal("1.5"), "1.5", True, None, "abc")
        ],
    ],
)
def test_invalid_policy_is_rejected_without_changing_database(field, value):
    policy = get_security_settings()
    previous = getattr(policy, field)
    setattr(policy, field, value)
    with pytest.raises(ValidationError) as error:
        policy.save()
    assert field in error.value.message_dict
    assert getattr(get_security_settings(), field) == previous


@pytest.mark.parametrize("days, minutes", [(0, 1), (1, 15), (90, 60)])
def test_valid_integer_boundaries(days, minutes):
    policy = get_security_settings()
    policy.password_max_age_days = days
    policy.idle_timeout_minutes = minutes
    policy.save()
    policy.refresh_from_db()
    assert (policy.password_max_age_days, policy.idle_timeout_minutes) == (
        days,
        minutes,
    )


def test_next_read_uses_current_values_and_timestamp(clock, django_assert_num_queries):
    original = get_security_settings()
    clock.advance(timedelta(days=1))
    original.save()
    changed_at = original.updated_at
    clock.advance(timedelta(minutes=1))
    original.levenshtein_enabled = False
    original.password_max_age_days = 30
    original.idle_timeout_minutes = 1
    original.save(
        update_fields=[
            "levenshtein_enabled",
            "password_max_age_days",
            "idle_timeout_minutes",
        ]
    )
    with django_assert_num_queries(1):
        current = get_security_settings()
    assert current is not original
    assert current.levenshtein_enabled is False
    assert current.password_max_age_days == 30
    assert current.idle_timeout_minutes == 1
    assert current.updated_at == clock.now() > changed_at


def test_fixed_identifier_is_enforced_by_model_and_database():
    with pytest.raises(ValidationError):
        SecuritySettings(id=2).save()
    with transaction.atomic(), pytest.raises(IntegrityError):
        SecuritySettings.objects.bulk_create([SecuritySettings(id=2)])
    assert SecuritySettings.objects.count() == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [("password_max_age_days", -1), ("idle_timeout_minutes", 0)],
)
def test_database_rejects_invalid_ranges_even_without_model_validation(field, value):
    with transaction.atomic(), pytest.raises(IntegrityError):
        SecuritySettings.objects.update(**{field: value})


@pytest.mark.parametrize("field", ["password_max_age_days", "idle_timeout_minutes"])
def test_fractional_queryset_update_is_not_silently_truncated(field):
    with pytest.raises(ValidationError):
        SecuritySettings.objects.update(**{field: 1.5})


@pytest.mark.parametrize("field", ["password_max_age_days", "idle_timeout_minutes"])
def test_database_rejects_fractional_expression_bypassing_field_conversion(field):
    with transaction.atomic(), pytest.raises(IntegrityError):
        SecuritySettings.objects.update(**{field: Value(1.5)})


def test_missing_policy_is_not_silently_replaced_with_defaults():
    SecuritySettings.objects.all().delete()
    with pytest.raises(SecuritySettings.DoesNotExist):
        get_security_settings()


@pytest.mark.django_db(transaction=True)
def test_initial_migrations_create_policy_from_empty_schema():
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("security", None)])
        executor = MigrationExecutor(connection)
        executor.migrate([("security", "0002_initial_settings")])
        historical_apps = executor.loader.project_state(
            [("security", "0002_initial_settings")]
        ).apps
        policy = historical_apps.get_model("security", "SecuritySettings").objects.get()
        assert policy.pk == 1
        assert policy.levenshtein_enabled is True
        assert policy.password_max_age_days == 0
        assert policy.idle_timeout_minutes == 15
    finally:
        MigrationExecutor(connection).migrate(latest)
