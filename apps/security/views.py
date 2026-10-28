"""Views for the restricted password-change context."""

from django.contrib import auth
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods

from .constants import (
    MIN_LEVENSHTEIN_DISTANCE,
    MIN_PASSWORD_LENGTH,
    PASSWORD_HISTORY_SIZE,
)
from .forms import PasswordChangeForm
from .selectors import get_security_settings
from .sessions import access_required


@sensitive_variables()
def _password_change(request):
    form = PasswordChangeForm(
        request.POST if request.method == "POST" else None,
        user=request.access_user,
        context=request.access_context,
    )
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except ValidationError as error:
            if hasattr(error, "error_dict"):
                for name, errors in error.error_dict.items():
                    form.add_error(name if name in form.fields else None, errors)
            else:
                form.add_error(None, error)
        else:
            auth.logout(request)
            return redirect("/login/?changed=1")
    return render(
        request,
        "security/password_change.html",
        {
            "form": form,
            "limited": request.access_context["scope"] == "limited",
            "policy": get_security_settings(),
            "minimum_length": MIN_PASSWORD_LENGTH,
            "history_size": PASSWORD_HISTORY_SIZE,
            "distance": MIN_LEVENSHTEIN_DISTANCE,
        },
    )


@sensitive_post_parameters("old_secret", "new_secret", "confirmation")
@access_required("limited")
@require_http_methods(["GET", "POST"])
def password_required(request):
    return _password_change(request)


@sensitive_post_parameters("old_secret", "new_secret", "confirmation")
@access_required("full")
@require_http_methods(["GET", "POST"])
def password_change(request):
    return _password_change(request)
