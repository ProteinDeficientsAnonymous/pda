"""Document library endpoints."""

from datetime import datetime

from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel
from users.permissions import PermissionKey

from community._shared import ErrorOut
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
    name: str
    parent_id: str | None = None


class FolderPatchIn(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    display_order: int | None = None


class DocumentIn(BaseModel):
    title: str
    folder_id: str
    content: str = ""


class DocumentPatchIn(BaseModel):
    title: str | None = None
    content: str | None = None
    folder_id: str | None = None


class DocumentOut(BaseModel):
    id: str
    title: str
    content: str
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
        parent_id=str(folder.parent_id) if folder.parent_id else None,
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


@router.get("/docs/folders/", response={200: list[DocFolderOut]}, auth=JWTAuth())
def list_folders(request):
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
        return Status(403, ErrorOut(detail="Permission denied."))

    parent = None
    if payload.parent_id:
        try:
            parent = DocFolder.objects.get(pk=payload.parent_id)
        except DocFolder.DoesNotExist:
            return Status(404, ErrorOut(detail="Parent folder not found."))

    folder = DocFolder.objects.create(name=payload.name, parent=parent)
    return Status(201, _folder_to_out(folder))


@router.put(
    "/docs/folders/reorder/",
    response={200: dict, 403: ErrorOut},
    auth=JWTAuth(),
)
def reorder_folders(request, payload: ReorderIn):
    if not _has_manage_docs(request.auth):
        return Status(403, ErrorOut(detail="Permission denied."))

    for i, fid in enumerate(payload.ids):
        DocFolder.objects.filter(pk=fid).update(display_order=i)
    return Status(200, {"detail": "Folders reordered."})


@router.patch(
    "/docs/folders/{folder_id}/",
    response={200: DocFolderOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_folder(request, folder_id: str, payload: FolderPatchIn):
    if not _has_manage_docs(request.auth):
        return Status(403, ErrorOut(detail="Permission denied."))

    try:
        folder = DocFolder.objects.get(pk=folder_id)
    except DocFolder.DoesNotExist:
        return Status(404, ErrorOut(detail="Folder not found."))

    updates = payload.model_dump(exclude_unset=True)
    if "parent_id" in updates:
        pid = updates.pop("parent_id")
        if pid is None:
            folder.parent = None
        else:
            try:
                folder.parent = DocFolder.objects.get(pk=pid)
            except DocFolder.DoesNotExist:
                return Status(404, ErrorOut(detail="Parent folder not found."))

    for key, value in updates.items():
        setattr(folder, key, value)
    folder.save()
    return Status(200, _folder_to_out(folder))


@router.delete(
    "/docs/folders/{folder_id}/",
    response={200: dict, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_folder(request, folder_id: str):
    if not _has_manage_docs(request.auth):
        return Status(403, ErrorOut(detail="Permission denied."))

    try:
        folder = DocFolder.objects.get(pk=folder_id)
    except DocFolder.DoesNotExist:
        return Status(404, ErrorOut(detail="Folder not found."))

    folder.delete()
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
        return Status(403, ErrorOut(detail="Permission denied."))

    try:
        folder = DocFolder.objects.get(pk=payload.folder_id)
    except DocFolder.DoesNotExist:
        return Status(404, ErrorOut(detail="Folder not found."))

    doc = Document.objects.create(
        title=payload.title,
        content=payload.content,
        folder=folder,
        created_by=request.auth,
    )
    return Status(201, _doc_to_out(doc))


@router.put(
    "/docs/reorder/",
    response={200: dict, 403: ErrorOut},
    auth=JWTAuth(),
)
def reorder_documents(request, payload: ReorderIn):
    if not _has_manage_docs(request.auth):
        return Status(403, ErrorOut(detail="Permission denied."))

    for i, did in enumerate(payload.ids):
        Document.objects.filter(pk=did).update(display_order=i)
    return Status(200, {"detail": "Documents reordered."})


@router.get(
    "/docs/{doc_id}/",
    response={200: DocumentOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def get_document(request, doc_id: str):
    try:
        doc = Document.objects.get(pk=doc_id)
    except Document.DoesNotExist:
        return Status(404, ErrorOut(detail="Document not found."))

    return Status(200, _doc_to_out(doc))


@router.patch(
    "/docs/{doc_id}/",
    response={200: DocumentOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_document(request, doc_id: str, payload: DocumentPatchIn):
    if not _has_manage_docs(request.auth):
        return Status(403, ErrorOut(detail="Permission denied."))

    try:
        doc = Document.objects.get(pk=doc_id)
    except Document.DoesNotExist:
        return Status(404, ErrorOut(detail="Document not found."))

    updates = payload.model_dump(exclude_unset=True)
    if "folder_id" in updates:
        fid = updates.pop("folder_id")
        try:
            doc.folder = DocFolder.objects.get(pk=fid)
        except DocFolder.DoesNotExist:
            return Status(404, ErrorOut(detail="Folder not found."))

    for key, value in updates.items():
        setattr(doc, key, value)
    doc.save()

    return Status(200, _doc_to_out(doc))


@router.delete(
    "/docs/{doc_id}/",
    response={200: dict, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_document(request, doc_id: str):
    if not _has_manage_docs(request.auth):
        return Status(403, ErrorOut(detail="Permission denied."))

    try:
        doc = Document.objects.get(pk=doc_id)
    except Document.DoesNotExist:
        return Status(404, ErrorOut(detail="Document not found."))

    doc.delete()
    return Status(200, {"detail": "Document deleted."})
