from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.accounts.models import User
from apps.documents.models import Document

pytestmark = pytest.mark.django_db


def test_demo_rejected_in_nonlocal_configuration(admin):
    with pytest.raises(CommandError):
        call_command("seed_demo", stdout=StringIO())


@override_settings(ALLOW_DEMO_DATA=True)
def test_demo_is_repeatable_and_resets_only_with_explicit_option(admin):
    admin_hash, admin_version = admin.password, admin.session_version
    output = StringIO()
    call_command("seed_demo", stdout=output)
    first = dict(
        User.objects.exclude(pk=admin.pk).values_list("username", "session_version")
    )
    assert len(first) == 6 and set(first.values()) == {2}
    assert User.objects.filter(role="MANAGER").count() == 1
    assert User.objects.filter(role="EDITOR").count() == 1
    assert User.objects.filter(role="EMPLOYEE").count() == 2
    assert User.objects.filter(role="READER").count() == 2
    assert Document.objects.count() == 3
    assert (
        Document.objects.filter(status="DRAFT").values("author").distinct().count() == 2
    )
    second_output = StringIO()
    call_command("seed_demo", stdout=second_output)
    assert (
        dict(
            User.objects.exclude(pk=admin.pk).values_list("username", "session_version")
        )
        == first
    )
    assert "kierownik:" not in second_output.getvalue()
    call_command("seed_demo", reset_passwords=True, stdout=StringIO())
    assert set(
        User.objects.exclude(pk=admin.pk).values_list("session_version", flat=True)
    ) == {3}
    admin.refresh_from_db()
    assert (admin.password, admin.session_version) == (admin_hash, admin_version)
    assert Document.objects.count() == 3
