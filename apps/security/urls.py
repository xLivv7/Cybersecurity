"""Password and security settings routes will be added incrementally."""

from django.urls import path

from .views import password_required

app_name = "security"
urlpatterns = [path("password/required/", password_required, name="password_required")]
