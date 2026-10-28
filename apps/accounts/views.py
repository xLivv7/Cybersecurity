"""Authentication, protected dashboard and POST-only logout endpoints."""

from django.contrib import auth
from django.core.exceptions import ValidationError
from django.middleware.csrf import rotate_token
from django.shortcuts import redirect, render
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods, require_POST

from apps.security.sessions import access_required, get_access, start_session

from .backends import LOGIN_ERROR
from .forms import LoginForm


@sensitive_post_parameters("password")
@sensitive_variables()
@require_http_methods(["GET", "POST"])
def login_view(request):
    access = get_access(request)
    if access is not None:
        return redirect(
            "home" if access[1]["scope"] == "full" else "security:password_required"
        )
    form = LoginForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            context = start_session(request, form.result, form.cleaned_data["password"])
        except ValidationError:
            form.add_error(None, LOGIN_ERROR)
        else:
            return redirect(
                "home" if context["scope"] == "full" else "security:password_required"
            )
    return render(request, "accounts/login.html", {"form": form})


@access_required("full")
@require_http_methods(["GET"])
def dashboard(request):
    return render(request, "accounts/dashboard.html", {"account": request.access_user})


@require_POST
def logout_view(request):
    auth.logout(request)
    rotate_token(request)
    return redirect("/login/?logged_out=1")
