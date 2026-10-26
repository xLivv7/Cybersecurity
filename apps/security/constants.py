"""Fixed policy values; only SecuritySettings fields are configurable."""

from datetime import timedelta

MIN_PASSWORD_LENGTH = 14
MIN_LEVENSHTEIN_DISTANCE = 4
PASSWORD_HISTORY_SIZE = 5
TEMPORARY_PASSWORD_LENGTH = 16
TEMPORARY_PASSWORD_LIFETIME = timedelta(hours=4)
