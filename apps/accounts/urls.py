"""Authentication routes; account management is added in E4."""

from django.urls import path

from . import admin_views
from .views import login_view, logout_view

app_name = "accounts"
urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("management/users/", admin_views.account_list, name="list"),
    path("management/users/new/", admin_views.account_create, name="create"),
    path("management/users/<int:pk>/edit/", admin_views.account_edit, name="edit"),
    path(
        "management/users/<int:pk>/<str:action>/",
        admin_views.account_confirm,
        name="action",
    ),
]
