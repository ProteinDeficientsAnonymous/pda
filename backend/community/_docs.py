"""Document library endpoints."""

import logging
from datetime import datetime

from config.audit import audit_log
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._content_render import render_content_payload
from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import DocFolder, Document

router = Router()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DocumentSummaryOut(BaseModel):
    id: str
    title: str
    display_order: int
    updated_at: datetime


class DocFolderOut(BaseModel):
    id: str
    name: str
    parent_id: str | None
    display_order: int
    children: list["DocFolderOut"]
    documents: list[DocumentSummaryOut]


class FolderIn(BaseModel):
    name: str = Field(max_length=FieldLimit.TITLE)
    parent_id: str | None = None


class FolderPatchIn(BaseModel):
    name: str | None = Field(default=None, max_length=FieldLimit.TITLE)
    parent_id: str | None = None
    display_order: int | None = None


class DocumentIn(BaseModel):
    title: str = Field(max_length=FieldLimit.TITLE)
    folder_id: str
    # Either Delta (Flutter) or ProseMirror (TipTap). Sending both is allowed
    # but content_pm wins in render_content_payload.
    content: str = Field(default="", max_length=FieldLimit.CONTENT)
    content_pm: str = Field(default="", max_length=FieldLimit.CONTENT)


class DocumentPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=FieldLimit.TITLE)
    content: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    content_pm: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    folder_id: str | None = None


class DocumentOut(BaseModel):
    id: str
    title: str
    content: str
    content_pm: str
    content_html: str
    folder_id: str
    display_order: int
    created_by_id: str | None
    created_at: datetime
    updated_at: datetime


class ReorderIn(BaseModel):
    ids: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _folder_to_out(folder: DocFolder) -> DocFolderOut:
    children = folder.children.prefetch_related("children", "documents").all()
    documents = folder.documents.all()
    return DocFolderOut(
        id=str(folder.id),
        name=folder.name,
        parent_id=str(folder.parent_id) if folder.parent_id else None,  # ty: ignore[unresolved-attribute]
        display_order=folder.display_order,
        children=[_folder_to_out(c) for c in children],
        documents=[
            DocumentSummaryOut(
                id=str(d.id),
                title=d.title,
                display_order=d.display_order,
                updated_at=d.updated_at,
            )
            for d in documents
        ],
    )


def _doc_to_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=str(doc.id),
        title=doc.title,
        content=doc.content,
        content_pm=doc.content_pm,
        content_html=doc.content_html,
        folder_id=str(doc.folder_id),
        display_order=doc.display_order,
        created_by_id=str(doc.created_by_id) if doc.created_by_id else None,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def _has_manage_docs(user) -> bool:
    return user.has_permission(PermissionKey.MANAGE_DOCUMENTS)


# ---------------------------------------------------------------------------
# Folder endpoints — named routes FIRST, parameterized LAST
# ---------------------------------------------------------------------------


@router.get(
    "/docs/folders/",
    response={200: list[DocFolderOut], 403: ErrorOut},
    auth=JWTAuth(),
)
def list_folders(request):
    if not _has_manage_docs(request.auth):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "list_folders",
                "required_permission": PermissionKey.MANAGE_DOCUMENTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_documents")
    top_level = DocFolder.objects.filter(parent__isnull=True).prefetch_related(
        "children", "documents", "children__documents"
    )
    return Status(200, [_folder_to_out(f) for f in top_level])


@router.post(
    "/docs/folders/",
    response={201: DocFolderOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def create_folder(request, payload: FolderIn):
    if not _has_manage_docs(request.auth):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "create_folder",
                "required_permission": PermissionKey.MANAGE_DOCUMENTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_documents")

    parent = None
    if payload.parent_id:
        try:
            parent = DocFolder.objects.get(pk=payload.parent_id)
        except DocFolder.DoesNotExist:
            raise_validation(Code.Docs.PARENT_FOLDER_NOT_FOUND, field="parent_id", status_code=404)

    folder = DocFolder.objects.create(name=payload.name, parent=parent)
    audit_log(
        logging.INFO,
        "doc_folder_created",
        request,
        target_type="doc_folder",
        target_id=str(folder.id),
        details={"name": folder.name, "parent_id": str(parent.id) if parent else None},
    )
    return Status(201, _folder_to_out(folder))


@router.put(
    "/docs/folders/reorder/",
    response={200: dict, 403: ErrorOut},
    auth=JWTAuth(),
)
def reorder_folders(request, payload: ReorderIn):
    if not _has_manage_docs(request.auth):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "reorder_folders",
                "required_permission": PermissionKey.MANAGE_DOCUMENTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_documents")

    for i, fid in enumerate(payload.ids):
        DocFolder.objects.filter(pk=fid).update(display_order=i)
    audit_log(logging.INFO, "doc_folders_reordered", request)
    return Status(200, {"detail": "Folders reordered."})


@router.patch(
    "/docs/folders/{folder_id}/",
    response={200: DocFolderOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_folder(request, folder_id: str, payload: FolderPatchIn):
    if not _has_manage_docs(request.auth):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="doc_folder",
            target_id=folder_id,
            details={
                "endpoint": "update_folder",
                "required_permission": PermissionKey.MANAGE_DOCUMENTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_documents")

    try:
        folder = DocFolder.objects.get(pk=folder_id)
    except DocFolder.DoesNotExist:
        raise_validation(Code.Docs.FOLDER_NOT_FOUND, status_code=404)

    updates = payload.model_dump(exclude_unset=True)
    if "parent_id" in updates:
        pid = updates.pop("parent_id")
        if pid is None:
            folder.parent = None
        else:
            try:
                folder.parent = DocFolder.objects.get(pk=pid)
            except DocFolder.DoesNotExist:
                raise_validation(
                    Code.Docs.PARENT_FOLDER_NOT_FOUND, field="parent_id", status_code=404
                )

    for key, value in updates.items():
        setattr(folder, key, value)
    folder.save()
    audit_log(
        logging.INFO,
        "doc_folder_updated",
        request,
        target_type="doc_folder",
        target_id=folder_id,
        details={"fields_changed": list(updates.keys())},
    )
    return Status(200, _folder_to_out(folder))


@router.delete(
    "/docs/folders/{folder_id}/",
    response={200: dict, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_folder(request, folder_id: str):
    if not _has_manage_docs(request.auth):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="doc_folder",
            target_id=folder_id,
            details={
                "endpoint": "delete_folder",
                "required_permission": PermissionKey.MANAGE_DOCUMENTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_documents")

    try:
        folder = DocFolder.objects.get(pk=folder_id)
    except DocFolder.DoesNotExist:
        raise_validation(Code.Docs.FOLDER_NOT_FOUND, status_code=404)

    folder_name = folder.name
    folder.delete()
    audit_log(
        logging.INFO,
        "doc_folder_deleted",
        request,
        target_type="doc_folder",
        target_id=folder_id,
        details={"name": folder_name},
    )
    return Status(200, {"detail": "Folder deleted."})


# ---------------------------------------------------------------------------
# Document endpoints — named routes FIRST, parameterized LAST
# ---------------------------------------------------------------------------


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
