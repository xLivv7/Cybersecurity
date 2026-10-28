"""Authentication endpoints; session dispatch is added in T013."""

from django.shortcuts import render
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods

from .forms import LoginForm


@sensitive_post_parameters("password")
@sensitive_variables()
@require_http_methods(["GET", "POST"])
def login_view(request):
    form = LoginForm(request.POST if request.method == "POST" else None)
    verified = request.method == "POST" and form.is_valid()
    return render(request, "accounts/login.html", {"form": form, "verified": verified})
