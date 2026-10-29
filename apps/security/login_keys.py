"""One opaque identity for equivalent logins, including unknown accounts."""

from django.utils.crypto import salted_hmac


def login_identity_key(login):
    return salted_hmac(
        "security.login-identity.v1", login.strip().casefold(), algorithm="sha256"
    ).hexdigest()
