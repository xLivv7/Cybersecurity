"""Exact unit-cost distance and its independently configurable policy rule."""

import pytest
from django.core.exceptions import ValidationError

from apps.security.passwords import levenshtein_distance
from apps.security.selectors import get_security_settings
from apps.security.validators import validate_permanent_password


@pytest.mark.parametrize(
    "first, second, distance",
    [
        ("", "", 0),
        ("", "żółć", 4),
        ("abc", "abc", 0),
        ("kitten", "sitting", 3),
        ("abc", "ab", 1),
        ("abc", "axc", 1),
        ("abc", "ab c", 1),
        ("Abc", "abc", 1),
        ("żółć", "zolc", 4),
        ("é", "e\u0301", 2),
    ],
)
def test_distance(first, second, distance):
    assert levenshtein_distance(first, second) == distance
    assert levenshtein_distance(second, first) == distance


@pytest.mark.django_db
@pytest.mark.parametrize("changes, accepted", [(3, False), (4, True)])
def test_threshold(changes, accepted, user_factory):
    old = "abcdefghijklmno"
    new = "Z" * changes + old[changes:]
    user = user_factory(password=old)
    if accepted:
        validate_permanent_password(user, old, new, new)
    else:
        with pytest.raises(ValidationError) as error:
            validate_permanent_password(user, old, new, new)
        assert "password_too_similar" in {
            item.code for item in error.value.error_dict["new_secret"]
        }


@pytest.mark.django_db
def test_disabling_rule_only_disables_distance_check(user_factory):
    old = "abcdefghijklmno"
    user = user_factory(password=old)
    policy = get_security_settings()
    policy.levenshtein_enabled = False
    policy.save()
    candidate = "Z" + old[1:]
    validate_permanent_password(user, old, candidate, candidate)
    for secret, confirmation, supplied_old in [
        (old, old, old),
        ("short", "short", old),
        ("password", "password", old),
        (candidate, "different", old),
        (candidate, candidate, "wrong"),
    ]:
        with pytest.raises(ValidationError):
            validate_permanent_password(user, supplied_old, secret, confirmation)
    policy.levenshtein_enabled = True
    policy.save()
    with pytest.raises(ValidationError):
        validate_permanent_password(user, old, candidate, candidate)
