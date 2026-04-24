"""Document endpoints (CRUD + reorder).

Folder endpoints live in ``_docs.py``. Shared schemas and helpers
(``DocumentOut``, ``_doc_to_out``, ``_has_manage_docs``, etc.) are imported
from there — single source of truth.
"""

import logging

from config.audit import audit_log
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from users.permissions import PermissionKey

from community._content_render import render_content_payload
from community._docs import (
    DocumentIn,
    DocumentOut,
    DocumentPatchIn,
    ReorderIn,
    _doc_to_out,
    _has_manage_docs,
)
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import DocFolder, Document

router = Router()


# Named routes FIRST, parameterized LAST — Ninja route ordering.


@router.post(
    "/docs/",
    response={201: DocumentOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def create_document(request, payload: DocumentIn):
    if not _has_manage_docs(request.auth):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "create_document",
                "required_permission": PermissionKey.MANAGE_DOCUMENTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_documents")

    try:
        folder = DocFolder.objects.get(pk=payload.folder_id)
    except DocFolder.DoesNotExist:
        raise_validation(Code.Docs.FOLDER_NOT_FOUND, status_code=404)

    rendered = render_content_payload(delta=payload.content, prosemirror=payload.content_pm)
    doc = Document.objects.create(
        title=payload.title,
        content=rendered.content,
        content_pm=rendered.content_pm,
        content_html=rendered.content_html,
        folder=folder,
        created_by=request.auth,
    )
    audit_log(
        logging.INFO,
        "document_created",
        request,
        target_type="document",
        target_id=str(doc.id),
        details={"title": doc.title, "folder_id": str(folder.id)},
    )
    return Status(201, _doc_to_out(doc))


@router.put(
    "/docs/reorder/",
    response={200: dict, 403: ErrorOut},
    auth=JWTAuth(),
)
def reorder_documents(request, payload: ReorderIn):
    if not _has_manage_docs(request.auth):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "reorder_documents",
                "required_permission": PermissionKey.MANAGE_DOCUMENTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_documents")

    for i, did in enumerate(payload.ids):
        Document.objects.filter(pk=did).update(display_order=i)
    audit_log(logging.INFO, "documents_reordered", request)
    return Status(200, {"detail": "Documents reordered."})


@router.get(
    "/docs/{doc_id}/",
    response={200: DocumentOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def get_document(request, doc_id: str):
    if not _has_manage_docs(request.auth):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "get_document",
                "required_permission": PermissionKey.MANAGE_DOCUMENTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_documents")
    try:
        doc = Document.objects.get(pk=doc_id)
    except Document.DoesNotExist:
        raise_validation(Code.Docs.DOCUMENT_NOT_FOUND, status_code=404)

    return Status(200, _doc_to_out(doc))


@router.patch(
    "/docs/{doc_id}/",
    response={200: DocumentOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_document(request, doc_id: str, payload: DocumentPatchIn):
    if not _has_manage_docs(request.auth):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="document",
            target_id=doc_id,
            details={
                "endpoint": "update_document",
                "required_permission": PermissionKey.MANAGE_DOCUMENTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_documents")

    try:
        doc = Document.objects.get(pk=doc_id)
    except Document.DoesNotExist:
        raise_validation(Code.Docs.DOCUMENT_NOT_FOUND, status_code=404)

    updates = payload.model_dump(exclude_unset=True)
    if "folder_id" in updates:
        fid = updates.pop("folder_id")
        try:
            doc.folder = DocFolder.objects.get(pk=fid)
        except DocFolder.DoesNotExist:
            raise_validation(Code.Docs.FOLDER_NOT_FOUND, status_code=404)

    # If either content format was sent, re-render HTML from the winner.
    content_sent = "content" in updates or "content_pm" in updates
    if content_sent:
        rendered = render_content_payload(
            delta=updates.pop("content", None),
            prosemirror=updates.pop("content_pm", None),
        )
        doc.content = rendered.content
        doc.content_pm = rendered.content_pm
        doc.content_html = rendered.content_html

    for key, value in updates.items():
        setattr(doc, key, value)
    doc.save()
    audit_log(
        logging.INFO,
        "document_updated",
        request,
        target_type="document",
        target_id=doc_id,
        details={"fields_changed": list(updates.keys())},
    )
    return Status(200, _doc_to_out(doc))


@router.delete(
    "/docs/{doc_id}/",
    response={200: dict, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_document(request, doc_id: str):
    if not _has_manage_docs(request.auth):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="document",
            target_id=doc_id,
            details={
                "endpoint": "delete_document",
                "required_permission": PermissionKey.MANAGE_DOCUMENTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_documents")

    try:
        doc = Document.objects.get(pk=doc_id)
    except Document.DoesNotExist:
        raise_validation(Code.Docs.DOCUMENT_NOT_FOUND, status_code=404)

    title = doc.title
    doc.delete()
    audit_log(
        logging.INFO,
        "document_deleted",
        request,
        target_type="document",
        target_id=doc_id,
        details={"title": title},
    )
    return Status(200, {"detail": "Document deleted."})
