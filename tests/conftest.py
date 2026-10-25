"""Shared account factories and a clock for tests using django.utils.timezone."""

from datetime import UTC, datetime, timedelta
from itertools import count

import pytest
from django.utils import timezone


class ControlledClock:
    def __init__(self):
        self._current = datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        return self._current

    def set(self, moment: datetime) -> None:
        if timezone.is_naive(moment):
            raise ValueError("Czas testowy musi zawierać strefę czasową.")
        self._current = moment.astimezone(UTC)

    def advance(self, delta: timedelta) -> None:
        self._current += delta


@pytest.fixture
def clock(monkeypatch):
    """Freeze timezone.now for this test; automatically restore it afterwards."""
    controlled = ControlledClock()
    monkeypatch.setattr(timezone, "now", controlled.now)
    return controlled


@pytest.fixture
def user_factory(db, django_user_model):
    """Create isolated accounts; omit password to keep it unusable by default."""
    sequence = count(1)

    def create_user(username=None, *, password=None, **fields):
        if username is None:
            username = f"user-{next(sequence)}"
        fields.setdefault("date_joined", timezone.now())
        return django_user_model.objects.create_user(
            username=username, password=password, **fields
        )

    return create_user


@pytest.fixture
def admin_factory(user_factory, django_user_model):
    """Create the single protected admin; the model still enforces uniqueness."""

    def create_admin(**fields):
        fields.setdefault("role", django_user_model.Role.ADMINISTRATOR)
        fields.setdefault("credential_mode", django_user_model.CredentialMode.INITIAL)
        return user_factory("ADMIN", **fields)

    return create_admin


@pytest.fixture
def admin(admin_factory):
    return admin_factory()
