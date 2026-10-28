"""Password and security settings routes will be added incrementally."""

from django.urls import path

from .views import password_change, password_required

app_name = "security"
urlpatterns = [
    path("password/required/", password_required, name="password_required"),
    path("password/change/", password_change, name="password_change"),
]
