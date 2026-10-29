"""Document routes will be added with the document model and access policies."""

from django.urls import path

from . import views

app_name = "documents"
urlpatterns = [
    path("", views.document_list, name="list"),
    path("new/", views.document_create, name="create"),
    path("<int:pk>/", views.document_detail, name="detail"),
    path("<int:pk>/edit/", views.document_edit, name="edit"),
    path("<int:pk>/<str:operation>/", views.document_transition, name="transition"),
]
