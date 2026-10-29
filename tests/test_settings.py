"""Verify settings in fresh processes without migrations or local database access."""

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SNAPSHOT = """
import importlib
import json
import os
settings = importlib.import_module(os.environ["DJANGO_SETTINGS_MODULE"])
print(json.dumps({
    "debug": settings.DEBUG,
    "hosts": settings.ALLOWED_HOSTS,
    "database": str(settings.DATABASES["default"]["NAME"]),
    "options": settings.DATABASES["default"]["OPTIONS"],
    "atomic_requests": settings.DATABASES["default"]["ATOMIC_REQUESTS"],
    "secure_session": settings.SESSION_COOKIE_SECURE,
    "secure_csrf": settings.CSRF_COOKIE_SECURE,
    "session_engine": settings.SESSION_ENGINE,
    "timezone": settings.TIME_ZONE,
    "use_tz": settings.USE_TZ,
    "hashers": settings.PASSWORD_HASHERS,
    "secret_from_environment": settings.SECRET_KEY == os.environ.get("DJANGO_SECRET_KEY"),
    "https_redirect": getattr(settings, "SECURE_SSL_REDIRECT", False),
}))
"""

NO_DOTENV = """
import dotenv
def reject_dotenv(*args, **kwargs):
    raise AssertionError("This environment must not load .env")
dotenv.load_dotenv = reject_dotenv
"""


def run_settings(environment, code=SNAPSHOT, *, variables=None, bootstrap=""):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    for name in ("DJANGO_SETTINGS_MODULE", "DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS"):
        env.pop(name, None)
    env["DJANGO_SETTINGS_MODULE"] = f"config.settings.{environment}"
    for name in (
        "TURNSTILE_SITE_KEY",
        "TURNSTILE_SECRET_KEY",
        "TURNSTILE_ALLOWED_HOSTNAMES",
    ):
        env.pop(name, None)
    if environment == "production":
        env.update(
            TURNSTILE_SITE_KEY="configured-site",
            TURNSTILE_SECRET_KEY="configured-secret",
            TURNSTILE_ALLOWED_HOSTNAMES="identity.example,www.identity.example",
        )
    for name, value in (variables or {}).items():
        if value is not None:
            env[name] = value
    return subprocess.run(
        [sys.executable, "-c", bootstrap + "\n" + code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


def successful_snapshot(result):
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_local_loads_dotenv_with_environment_precedence(tmp_path):
    file_key = secrets.token_urlsafe(64)
    env_key = secrets.token_urlsafe(64)
    (tmp_path / ".env").write_text(
        f"DJANGO_SECRET_KEY={file_key}\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n",
        encoding="utf-8",
    )
    bootstrap = (
        "from pathlib import Path\n"
        "import config.settings.base as base\n"
        f"base.BASE_DIR = Path({str(tmp_path)!r})\n"
    )
    data = successful_snapshot(
        run_settings(
            "local", variables={"DJANGO_SECRET_KEY": env_key}, bootstrap=bootstrap
        )
    )
    assert data["secret_from_environment"] is True
    assert data["hosts"] == ["localhost", "127.0.0.1"]
    assert data["debug"] is True
    assert data["secure_session"] is False
    assert data["secure_csrf"] is False
    # The existing process environment must take precedence over .env.
    result = run_settings(
        "local",
        "import os,config.settings.local as s; "
        "assert s.SECRET_KEY == os.environ['DJANGO_SECRET_KEY']; "
        f"assert s.SECRET_KEY != {file_key!r}",
        variables={"DJANGO_SECRET_KEY": env_key},
        bootstrap=bootstrap,
    )
    assert result.returncode == 0, result.stderr


def test_local_requires_secret_when_dotenv_is_absent(tmp_path):
    bootstrap = (
        "from pathlib import Path\nimport config.settings.base as base\n"
        f"base.BASE_DIR = Path({str(tmp_path)!r})\n"
    )
    result = run_settings("local", bootstrap=bootstrap)
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_test_settings_are_isolated_and_keep_real_hasher():
    data = successful_snapshot(
        run_settings(
            "test",
            variables={
                "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
                "DJANGO_ALLOWED_HOSTS": "untrusted.example",
            },
            bootstrap=NO_DOTENV,
        )
    )
    assert data["database"] == ":memory:"
    assert data["secret_from_environment"] is False
    assert data["hosts"][0] == "testserver"
    assert data["debug"] is False
    assert data["options"]["transaction_mode"] == "IMMEDIATE"
    assert data["atomic_requests"] is False
    assert data["timezone"] == "Europe/Warsaw"
    assert data["use_tz"] is True
    assert data["session_engine"] == "django.contrib.sessions.backends.db"
    assert data["hashers"] == ["django.contrib.auth.hashers.Argon2PasswordHasher"]


@pytest.mark.parametrize("key", [None, "", "short", "x" * 64, "django-insecure-" * 5])
def test_production_rejects_missing_or_weak_secret(key):
    result = run_settings(
        "production",
        variables={"DJANGO_SECRET_KEY": key, "DJANGO_ALLOWED_HOSTS": "example.com"},
        bootstrap=NO_DOTENV,
    )
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr
    if key:
        assert key not in result.stderr


@pytest.mark.parametrize("hosts", [None, "", " , ", "*", "example.com,*"])
def test_production_requires_explicit_hosts(hosts):
    result = run_settings(
        "production",
        variables={
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
            "DJANGO_ALLOWED_HOSTS": hosts,
        },
        bootstrap=NO_DOTENV,
    )
    assert result.returncode != 0
    assert "DJANGO_ALLOWED_HOSTS" in result.stderr


def test_production_security_does_not_depend_on_dotenv_or_debug_env():
    data = successful_snapshot(
        run_settings(
            "production",
            variables={
                "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
                "DJANGO_ALLOWED_HOSTS": " identity.example, www.identity.example ",
                "DJANGO_DEBUG": "True",
            },
            bootstrap=NO_DOTENV,
        )
    )
    assert data["hosts"] == ["identity.example", "www.identity.example"]
    assert data["debug"] is False
    assert data["https_redirect"] is True
    assert data["secure_session"] is True
    assert data["secure_csrf"] is True


def test_skeleton_renders_without_database_queries_and_has_no_admin_route():
    result = run_settings(
        "test",
        """
import django
django.setup()
from django.contrib.staticfiles import finders
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.conf import settings
assert 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE
with CaptureQueriesContext(connection) as queries:
    response = Client(enforce_csrf_checks=True).get('/login/')
    assert response.status_code == 200
    assert 'lang="pl"' in response.text
    assert '/static/css/base.css' in response.text
    assert Client().get('/admin/').status_code == 404
assert len(queries) == 0
assert finders.find('css/base.css')
""",
    )
    assert result.returncode == 0, result.stderr


def test_database_uses_immediate_transactions_in_memory():
    result = run_settings(
        "test",
        """
import django
django.setup()
from django.db import connection,transaction
from django.test.utils import CaptureQueriesContext
with CaptureQueriesContext(connection) as queries:
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
assert any(q['sql'] == 'BEGIN IMMEDIATE' for q in queries)
assert connection.settings_dict['NAME'] == ':memory:'
""",
    )
    assert result.returncode == 0, result.stderr


def test_wsgi_and_asgi_entry_points_honor_explicit_settings():
    result = run_settings(
        "test",
        """
from config.wsgi import application as wsgi
from config.asgi import application as asgi
from django.conf import settings
assert callable(wsgi) and callable(asgi)
assert settings.SETTINGS_MODULE == 'config.settings.test'
""",
        bootstrap=NO_DOTENV,
    )
    assert result.returncode == 0, result.stderr
