"""Administrator edits current policy through a validated service."""

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.admin_views import add_errors, administrator_required
from apps.accounts.services import require_administrator

from .models import SecuritySettings
from .selectors import get_security_settings
from .services import database_operation


class SecuritySettingsForm(forms.ModelForm):
    class Meta:
        model = SecuritySettings
        fields = [
            "levenshtein_enabled",
            "password_max_age_days",
            "idle_timeout_minutes",
        ]
        help_texts = {
            "password_max_age_days": "0 wyłącza okresowe wygasanie. Dodatnia liczba oznacza pełne okresy 24 godzin.",
            "idle_timeout_minutes": "Dodatnia całkowita liczba minut. Zmiana dotyczy również istniejących sesji.",
        }


@database_operation
def update_security_settings(actor, **values):
    with transaction.atomic():
        require_administrator(actor)
        policy = get_security_settings()
        for name in SecuritySettingsForm.Meta.fields:
            setattr(policy, name, values[name])
        policy.save()
        return policy


@administrator_required
@require_http_methods(["GET", "POST"])
def security_settings(request):
    form = SecuritySettingsForm(
        request.POST if request.method == "POST" else None,
        instance=get_security_settings(),
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_security_settings(request.access_user, **form.cleaned_data)
        except ValidationError as error:
            add_errors(form, error)
        else:
            messages.success(request, "Zmieniono ustawienia bezpieczeństwa.")
            return redirect("security:settings")
    return render(
        request,
        "shared/form.html",
        {
            "form": form,
            "title": "Ustawienia bezpieczeństwa",
            "description": "Stałe zasady: minimum 14 znaków, odległość 4, historia 5 haseł. Hasło tymczasowe: 16 znaków i ważność 4 godzin.",
        },
    )
