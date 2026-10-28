"""Polish login form with exact password input and a uniform refusal."""

from django import forms
from django.core.exceptions import ValidationError
from django.views.decorators.debug import sensitive_variables

from .backends import LOGIN_ERROR, authenticate_login


class LoginForm(forms.Form):
    login = forms.CharField(
        label="Login",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Hasło",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    @sensitive_variables()
    def clean(self):
        cleaned = super().clean()
        if "login" in cleaned and "password" in cleaned:
            self.result = authenticate_login(cleaned["login"], cleaned["password"])
            if self.result is None:
                raise ValidationError(LOGIN_ERROR, code="invalid_login")
        return cleaned
