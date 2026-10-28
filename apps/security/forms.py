"""Password fields preserve exact input and delegate all rules to the service."""

from django import forms
from django.views.decorators.debug import sensitive_variables

from .services import ChangeReason, change_password


class PasswordChangeForm(forms.Form):
    old_secret = forms.CharField(
        label="Dotychczasowe hasło",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    new_secret = forms.CharField(
        label="Nowe hasło",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    confirmation = forms.CharField(
        label="Powtórz nowe hasło",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, *args, user, context, **kwargs):
        super().__init__(*args, **kwargs)
        self.user, self.context = user, context
        if context["reason"] == ChangeReason.RESET:
            self.fields["old_secret"].label = "Hasło tymczasowe"

    @sensitive_variables()
    def save(self):
        return change_password(
            self.user.pk,
            self.cleaned_data["old_secret"],
            self.cleaned_data["new_secret"],
            self.cleaned_data["confirmation"],
            reason=self.context["reason"] or ChangeReason.VOLUNTARY,
            expected_version=self.context["version"],
            credential_id=self.context["credential_id"],
        )
