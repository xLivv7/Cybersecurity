"""The application's account panel, independent of Django Admin."""

from functools import wraps

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.debug import sensitive_variables
from django.views.decorators.http import require_http_methods

from apps.security.sessions import access_required

from .models import User
from .services import (
    account_action,
    create_account,
    edit_account,
    require_administrator,
)


def administrator_required(view):
    @access_required("full")
    @wraps(view)
    def guarded(request, *args, **kwargs):
        require_administrator(request.access_user)
        return view(request, *args, **kwargs)

    return guarded


class AccountForm(forms.Form):
    first_name = forms.CharField(label="Imię", max_length=150, required=False)
    last_name = forms.CharField(label="Nazwisko", max_length=150, required=False)
    role = forms.ChoiceField(
        label="Rola",
        initial=User.Role.READER,
        choices=[
            item for item in User.Role.choices if item[0] != User.Role.ADMINISTRATOR
        ],
    )


class CreateAccountForm(AccountForm):
    username = forms.CharField(label="Login", max_length=150)
    field_order = ["username", "first_name", "last_name", "role"]


class ConfirmationForm(forms.Form):
    confirm = forms.BooleanField(label="Potwierdzam wykonanie tej operacji")


def add_errors(form, error):
    if hasattr(error, "error_dict"):
        for name, errors in error.error_dict.items():
            form.add_error(name if name in form.fields else None, errors)
    else:
        form.add_error(None, error)


@administrator_required
@require_http_methods(["GET"])
def account_list(request):
    return render(
        request,
        "accounts/list.html",
        {
            "accounts": User.objects.filter(deleted_at__isnull=True).order_by(
                "login_key"
            )
        },
    )


@sensitive_variables()
@administrator_required
@require_http_methods(["GET", "POST"])
def account_create(request):
    form = CreateAccountForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            user, issued = create_account(request.access_user, **form.cleaned_data)
        except ValidationError as error:
            add_errors(form, error)
        else:
            return render(
                request, "accounts/issued.html", {"account": user, "issued": issued}
            )
    return render(request, "shared/form.html", {"form": form, "title": "Nowe konto"})


@administrator_required
@require_http_methods(["GET", "POST"])
def account_edit(request, pk):
    user = get_object_or_404(User, pk=pk, deleted_at__isnull=True)
    form = AccountForm(
        request.POST if request.method == "POST" else None,
        initial={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
        },
    )
    if user.login_key == "admin":
        form.fields["role"].choices = User.Role.choices
        form.fields["role"].disabled = True
    if request.method == "POST" and form.is_valid():
        try:
            edit_account(request.access_user, user.pk, **form.cleaned_data)
        except ValidationError as error:
            add_errors(form, error)
        else:
            messages.success(request, "Zapisano dane konta.")
            return redirect("accounts:list")
    return render(
        request,
        "shared/form.html",
        {"form": form, "title": f"Edycja konta {user.username}"},
    )


ACTION_LABELS = {
    "block": ("Zablokuj", "Konto utraci dostęp, a jego sesje zostaną unieważnione."),
    "unblock": (
        "Odblokuj",
        "Użytkownik będzie mógł się zalogować; stare sesje nie zostaną przywrócone.",
    ),
    "delete": (
        "Usuń",
        "Konto utraci dostęp i zniknie z listy. Login pozostanie zarezerwowany, a autorstwo dokumentów zachowane.",
    ),
    "reset": (
        "Resetuj hasło",
        "Dotychczasowe hasło i sesje przestaną działać. Nowe hasło tymczasowe będzie ważne 4 godziny.",
    ),
}


@sensitive_variables()
@administrator_required
@require_http_methods(["GET", "POST"])
def account_confirm(request, pk, action):
    from django.http import Http404

    if action not in ACTION_LABELS:
        raise Http404
    user = get_object_or_404(User, pk=pk, deleted_at__isnull=True)
    label, effect = ACTION_LABELS[action]
    form = ConfirmationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            issued = account_action(request.access_user, pk, action)
        except ValidationError as error:
            add_errors(form, error)
        else:
            if issued is not None:
                return render(
                    request, "accounts/issued.html", {"account": user, "issued": issued}
                )
            messages.success(request, "Operacja została wykonana.")
            return redirect("accounts:list")
    return render(
        request,
        "shared/form.html",
        {"form": form, "title": f"{label}: {user.username}", "description": effect},
    )
