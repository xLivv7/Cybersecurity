"""Root routes; application modules add their endpoints incrementally."""

from django.urls import include, path

from apps.accounts.views import dashboard

handler403 = "apps.accounts.errors.forbidden"
handler404 = "apps.accounts.errors.not_found"

urlpatterns = [
    path("", dashboard, name="home"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.security.urls")),
    path("documents/", include("apps.documents.urls")),
]
