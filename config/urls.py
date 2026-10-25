"""Root routes; application modules add their endpoints incrementally."""

from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.security.urls")),
    path("documents/", include("apps.documents.urls")),
]
