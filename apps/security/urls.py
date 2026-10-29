"""Password and security settings routes will be added incrementally."""

from django.urls import path

from .settings_views import security_settings
from .views import password_change, password_required, session_status

app_name = "security"
urlpatterns = [
    path("session/status/", session_status, name="session_status"),
    path("management/security/", security_settings, name="settings"),
    path("password/required/", password_required, name="password_required"),
    path("password/change/", password_change, name="password_change"),
]
