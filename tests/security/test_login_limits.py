"""HTTP decisions, exact deadlines and real SQLite races for login limits."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event, current_thread

import pytest
from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import Client

from apps.accounts import backends
from apps.security import login_limits
from apps.security.login_keys import login_identity_key
from apps.security.models import LoginAttemptState, SecurityEvent, TemporaryCredential
from apps.security.selectors import get_security_settings
from apps.security.services import issue_temporary_credential
from apps.security.sessions import CONTEXT_KEY

pytestmark = pytest.mark.django_db
PASSWORD = "previous long passphrase"


def post(client, password="wrong", login="reader"):
    return client.post("/login/", {"login": login, "password": password})


def counter(login="reader"):
    return LoginAttemptState.objects.get(identity_key=login_identity_key(login))


def policy(limit):
    settings = get_security_settings()
    settings.login_failure_limit = limit
    settings.save()


@pytest.mark.parametrize("kind", ["permanent", "initial", "temporary", "missing"])
def test_threshold_and_blocked_correct_password(
    kind, user_factory, admin_factory, client, clock
):
    login, password = "reader", PASSWORD
    credential = None
    if kind == "initial":
        login = "ADMIN"
        user = admin_factory(password=PASSWORD)
    elif kind == "missing":
        user = None
    else:
        user = user_factory(login, password=PASSWORD, credential_mode="PERMANENT")
        if kind == "temporary":
            credential = issue_temporary_credential(user.pk)
            password = credential.secret
    if user:
        user.refresh_from_db()
        version = user.session_version
    policy(2)
    post(client, login=login)
    assert counter(login).failure_count == 1
    assert counter(login).blocked_until is None
    post(client, login=login)
    deadline = clock.now() + timedelta(seconds=900)
    assert counter(login).blocked_until == deadline
    assert post(client, password, login).status_code == 200
    assert counter(login).failure_count == 2
    assert counter(login).blocked_until == deadline
    assert CONTEXT_KEY not in client.session
    if user:
        user.refresh_from_db()
        assert user.is_active and user.session_version == version
    if credential:
        assert (
            TemporaryCredential.objects.get(pk=credential.credential_id).consumed_at
            is None
        )
    assert SecurityEvent.objects.filter(category="credential_failure").count() == 2
    assert SecurityEvent.objects.filter(category="account_locked").count() == 1


@pytest.mark.parametrize("microseconds,allowed", [(-1, False), (0, True), (1, True)])
def test_exact_deadline_and_no_renewal(
    microseconds, allowed, user_factory, client, clock
):
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    policy(1)
    post(client)
    state = counter()
    clock.advance(timedelta(seconds=900, microseconds=microseconds))
    response = post(client, PASSWORD)
    assert response.status_code == (302 if allowed else 200)
    if allowed:
        assert counter().failure_count == 0 and counter().blocked_until is None
    else:
        assert counter().blocked_until == state.blocked_until
        assert counter().version == state.version
        assert counter().updated_at == state.updated_at


def test_expired_lock_starts_new_count(client, clock):
    policy(2)
    post(client)
    post(client)
    clock.advance(timedelta(seconds=900))
    post(client)
    assert counter().failure_count == 1
    assert counter().blocked_until is None


def test_success_resets_counter_and_normalization_is_shared(user_factory, client):
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    post(client, login=" READER ")
    assert counter().failure_count == 1
    assert post(client, PASSWORD).status_code == 302
    assert counter().failure_count == 0
    client.post("/logout/")
    post(client)
    assert counter().failure_count == 1
    assert LoginAttemptState.objects.count() == 1


def test_policy_change_applies_without_changing_existing_deadline(
    user_factory, client, clock
):
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    post(client)
    post(client)
    policy(2)
    assert post(client, PASSWORD).status_code == 200
    deadline = counter().blocked_until
    policy(50)
    clock.advance(timedelta(seconds=20))
    assert post(client, PASSWORD).status_code == 200
    assert counter().blocked_until == deadline


def test_policy_rechecked_after_password_verification(
    user_factory, client, monkeypatch
):
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    post(client)
    original = login_limits.authenticate_login

    def lower(*args):
        result = original(*args)
        policy(1)
        return result

    monkeypatch.setattr(login_limits, "authenticate_login", lower)
    assert post(client, PASSWORD).status_code == 200
    assert counter().blocked_until is not None
    assert CONTEXT_KEY not in client.session


def test_reset_after_verification_cannot_grant_old_password(
    user_factory, client, monkeypatch
):
    user = user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    original = login_limits.authenticate_login

    def reset(*args):
        result = original(*args)
        issue_temporary_credential(user.pk)
        return result

    monkeypatch.setattr(login_limits, "authenticate_login", reset)
    assert post(client, PASSWORD).status_code == 200
    assert CONTEXT_KEY not in client.session
    assert not LoginAttemptState.objects.exists()  # transaction rolled back


def test_invalid_fields_csrf_and_get_do_not_count(client):
    client.get("/login/")
    client.post("/login/", {"login": "reader"})
    client.post("/login/", {"login": "x" * 151, "password": "wrong"})
    protected = Client(enforce_csrf_checks=True)
    assert post(protected).status_code == 403
    assert not LoginAttemptState.objects.exists()


def test_existing_session_survives_login_block(user_factory, client):
    user_factory("reader", password=PASSWORD, credential_mode="PERMANENT")
    post(client, PASSWORD)
    policy(1)
    other = Client()
    post(other)
    assert counter().blocked_until is not None
    assert client.get("/").status_code == 200


def thread_login(password):
    try:
        response = post(Client(), password)
        return CONTEXT_KEY in response.wsgi_request.session
    finally:
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_concurrent_failures_do_not_lose_increment(file_database, monkeypatch):
    barrier = Barrier(2)
    original = login_limits.authenticate_login

    def together(*args):
        result = original(*args)
        barrier.wait(timeout=15)
        return result

    monkeypatch.setattr(login_limits, "authenticate_login", together)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(thread_login, ["wrong", "wrong"]))
    assert results == [False, False]
    assert counter().failure_count == counter().version == 2
    assert SecurityEvent.objects.filter(category="credential_failure").count() == 2


@pytest.mark.django_db(transaction=True)
def test_block_wins_against_inflight_correct_password(file_database, monkeypatch):
    get_user_model().objects.create_user(
        "reader", password=PASSWORD, credential_mode="PERMANENT"
    )
    policy(1)
    verified, release = Event(), Event()
    original = login_limits.authenticate_login

    def wait(*args):
        result = original(*args)
        if current_thread().name.startswith("correct"):
            verified.set()
            assert release.wait(timeout=15)
        return result

    monkeypatch.setattr(login_limits, "authenticate_login", wait)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="correct") as executor:
        future = executor.submit(thread_login, PASSWORD)
        try:
            assert verified.wait(timeout=15)
            assert post(Client()).status_code == 200
        finally:
            release.set()
        assert future.result(timeout=20) is False
    assert counter().failure_count == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_temporary_logins_only_one_consumes_and_hashes_outside_lock(
    file_database, monkeypatch
):
    user = get_user_model().objects.create_user("reader")
    issued = issue_temporary_credential(user.pk)
    original_check = backends.check_password
    checks = []

    def outside(*args):
        assert not connection.in_atomic_block
        checks.append(True)
        return original_check(*args)

    monkeypatch.setattr(backends, "check_password", outside)
    # Any second hash from the old session-consumption path would be inside a lock.
    monkeypatch.setattr("apps.security.services.check_password", outside)
    original = login_limits.authenticate_login
    barrier = Barrier(2)

    def together(*args):
        result = original(*args)
        barrier.wait(timeout=15)
        return result

    monkeypatch.setattr(login_limits, "authenticate_login", together)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(thread_login, [issued.secret, issued.secret]))
    assert sorted(results) == [False, True]
    assert len(checks) == 2
    assert (
        TemporaryCredential.objects.get(pk=issued.credential_id).consumed_at is not None
    )
