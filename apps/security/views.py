"""Views for the restricted password-change context."""

from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .sessions import access_required


@access_required("limited")
@require_http_methods(["GET"])
def password_required(request):
    return render(request, "security/password_required.html")
