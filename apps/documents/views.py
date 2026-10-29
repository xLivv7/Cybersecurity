from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.admin_views import add_errors
from apps.security.sessions import access_required

from .models import Document
from .policies import can
from .selectors import visible_documents
from .services import create_document, edit_document, transition_document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 12})}


@access_required("full", return_to=True)
@require_http_methods(["GET"])
def document_list(request):
    return render(
        request,
        "documents/list.html",
        {
            "documents": visible_documents(request.access_user),
            "can_create": can(request.access_user, "create"),
        },
    )


@access_required("full", return_to=True)
@require_http_methods(["GET"])
def document_detail(request, pk):
    document = get_object_or_404(Document.objects.select_related("author"), pk=pk)
    if not can(request.access_user, "read", document):
        raise PermissionDenied
    return render(
        request,
        "documents/detail.html",
        {
            "document": document,
            "can_edit": can(request.access_user, "edit", document),
            "can_publish": can(request.access_user, "publish", document),
            "can_withdraw": can(request.access_user, "withdraw", document),
        },
    )


@access_required("full", return_to=True)
@require_http_methods(["GET", "POST"])
def document_create(request):
    if not can(request.access_user, "create"):
        raise PermissionDenied
    form = DocumentForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            document = create_document(request.access_user, **form.cleaned_data)
        except ValidationError as error:
            add_errors(form, error)
        else:
            messages.success(request, "Utworzono szkic.")
            return redirect("documents:detail", pk=document.pk)
    return render(request, "shared/form.html", {"form": form, "title": "Nowy szkic"})


@access_required("full", return_to=True)
@require_http_methods(["GET", "POST"])
def document_edit(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if not can(request.access_user, "edit", document):
        raise PermissionDenied
    form = DocumentForm(
        request.POST if request.method == "POST" else None, instance=document
    )
    if request.method == "POST" and form.is_valid():
        try:
            edit_document(request.access_user, pk, **form.cleaned_data)
        except ValidationError as error:
            add_errors(form, error)
        else:
            messages.success(request, "Zapisano szkic.")
            return redirect("documents:detail", pk=pk)
    return render(request, "shared/form.html", {"form": form, "title": "Edytuj szkic"})


@access_required("full", return_to=True)
@require_POST
def document_transition(request, pk, operation):
    get_object_or_404(Document, pk=pk)
    try:
        transition_document(request.access_user, pk, operation)
    except ValidationError:
        messages.error(
            request, "Nie udało się zapisać. Odśwież dokument i ponów operację."
        )
    return redirect("documents:detail", pk=pk)
