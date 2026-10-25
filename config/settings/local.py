"""Local development settings; only this environment loads .env."""

from dotenv import load_dotenv

from ._env import hosts_from_environment, secret_key_from_environment
from .base import *  # noqa: F403
from .base import BASE_DIR

load_dotenv(BASE_DIR / ".env", override=False)

SECRET_KEY = secret_key_from_environment()
DEBUG = True
ALLOWED_HOSTS = hosts_from_environment("localhost,127.0.0.1,[::1]")
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
