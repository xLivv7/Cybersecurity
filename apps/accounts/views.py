"""Authentication, protected dashboard and POST-only logout endpoints."""

from math import ceil

from django.contrib import auth
from django.core.exceptions import ValidationError
from django.middleware.csrf import rotate_token
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods, require_POST

from apps.security import captcha
from apps.security.login_keys import login_identity_key
from apps.security.login_limits import attempt_login, get_login_block
from apps.security.models import SecurityEvent
from apps.security.sessions import access_required, get_access

from .backends import LOGIN_ERROR
from .forms import LoginForm


def _login_context(request, form):
    context = {"form": form, **captcha.widget_context(request, "login")}
    login = getattr(form, "cleaned_data", {}).get("login")
    deadline = get_login_block(login) if login else None
    if deadline is not None:
        seconds = max(0, ceil((deadline - timezone.now()).total_seconds()))
        context.update(
            login_block_seconds=seconds,
            login_block_time=f"{seconds // 60}:{seconds % 60:02d}",
        )
    return context


@sensitive_post_parameters("password", "cf-turnstile-response", "website")
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
        login = form.cleaned_data["login"]
        if form.cleaned_data["website"]:
            SecurityEvent.objects.create(
                category="honeypot", identity_key=login_identity_key(login)
            )
            form.add_error(None, LOGIN_ERROR)
            return render(request, "accounts/login.html", _login_context(request, form))
        if get_login_block(login) is not None:
            form.add_error(None, LOGIN_ERROR)
            return render(request, "accounts/login.html", _login_context(request, form))
        if not captcha.validate_request(request, "login"):
            SecurityEvent.objects.create(
                category="captcha_rejected", identity_key=login_identity_key(login)
            )
            form.add_error(None, captcha.CAPTCHA_ERROR)
            return render(request, "accounts/login.html", _login_context(request, form))
        try:
            attempt = attempt_login(
                request, form.cleaned_data["login"], form.cleaned_data["password"]
            )
        except ValidationError:
            auth.logout(request)
            form.add_error(None, LOGIN_ERROR)
        else:
            context = attempt.context
            if context is None:
                form.add_error(None, LOGIN_ERROR)
                return render(
                    request, "accounts/login.html", _login_context(request, form)
                )
            next_url = request.GET.get("next", "")
            if (
                context["scope"] == "full"
                and next_url.startswith("/")
                and not next_url.startswith("//")
                and url_has_allowed_host_and_scheme(
                    next_url, {request.get_host()}, require_https=request.is_secure()
                )
            ):
                return redirect(next_url)
            return redirect(
                "home" if context["scope"] == "full" else "security:password_required"
            )
    return render(request, "accounts/login.html", _login_context(request, form))


@access_required("full")
@require_http_methods(["GET"])
def dashboard(request):
    from apps.documents.policies import can
    from apps.documents.selectors import visible_documents
    from apps.security.selectors import get_security_settings

    return render(
        request,
        "accounts/dashboard.html",
        {
            "account": request.access_user,
            "document_count": visible_documents(request.access_user).count(),
            "can_create": can(request.access_user, "create"),
            "policy": get_security_settings(),
        },
    )


@require_POST
def logout_view(request):
    auth.logout(request)
    rotate_token(request)
    return redirect("/login/?logged_out=1")
