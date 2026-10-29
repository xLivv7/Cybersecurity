"""Polish login form with exact password input and a uniform refusal."""

from django import forms


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
