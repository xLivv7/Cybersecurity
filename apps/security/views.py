"""Standard and restricted password-change views."""

import math
from datetime import datetime

from django.contrib import auth
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_GET, require_http_methods

from .constants import (
    MIN_LEVENSHTEIN_DISTANCE,
    MIN_PASSWORD_LENGTH,
    PASSWORD_HISTORY_SIZE,
)
from .forms import PasswordChangeForm
from .middleware import passive_view
from .selectors import get_security_settings
from .sessions import access_required, get_access


@passive_view
@require_GET
def session_status(request):
    """Expose only a deadline and scope; polling never renews activity."""
    access = get_access(request)
    if access is None:
        return JsonResponse({"active": False})
    _, context = access
    now = timezone.now()
    remaining = (
        get_security_settings().idle_timeout_minutes * 60
        - (now - datetime.fromisoformat(context["last_activity"])).total_seconds()
    )
    if context.get("expires_at"):
        remaining = min(
            remaining,
            (datetime.fromisoformat(context["expires_at"]) - now).total_seconds(),
        )
    if remaining <= 0:
        auth.logout(request)
        return JsonResponse({"active": False})
    return JsonResponse(
        {
            "active": True,
            "scope": context["scope"],
            "remaining_seconds": math.ceil(remaining),
        }
    )


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
