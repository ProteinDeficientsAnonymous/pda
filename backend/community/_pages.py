"""Editable pages endpoints."""

import logging
from datetime import datetime

from config.audit import audit_log
from django.contrib.auth.models import AnonymousUser
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel
from users.permissions import PermissionKey

from community._delta_html import delta_to_html
from community._shared import ErrorOut, _optional_jwt
from community.models import EditablePage, PageVisibility

router = Router()


class EditablePageOut(BaseModel):
    slug: str
    content: str
    content_html: str
    visibility: str
    updated_at: datetime


class EditablePagePatchIn(BaseModel):
    content: str | None = None
    visibility: str | None = None


def _page_out(page: EditablePage) -> EditablePageOut:
    return EditablePageOut(
        slug=page.slug,
        content=page.content,
        content_html=page.content_html,
        visibility=page.visibility,
        updated_at=page.updated_at,
    )


@router.get("/pages/{slug}/", response={200: EditablePageOut, 403: ErrorOut}, auth=_optional_jwt)
def get_page(request, slug: str):
    default_vis = PageVisibility.MEMBERS_ONLY if slug == "volunteer" else PageVisibility.PUBLIC
    page = EditablePage.get_or_create_page(slug, default_visibility=default_vis)

    if page.visibility == PageVisibility.MEMBERS_ONLY:
        if isinstance(request.auth, AnonymousUser):
            return Status(403, ErrorOut(detail="Members only."))

    return Status(200, _page_out(page))


@router.patch("/pages/{slug}/", response={200: EditablePageOut, 403: ErrorOut}, auth=JWTAuth())
def update_page(request, slug: str, payload: EditablePagePatchIn):
    if not request.auth.has_permission(PermissionKey.EDIT_GUIDELINES):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="editable_page",
            target_id=slug,
            details={
                "endpoint": "update_page",
                "required_permission": PermissionKey.EDIT_GUIDELINES,
            },
        )
        return Status(403, ErrorOut(detail="Permission denied."))

    default_vis = PageVisibility.MEMBERS_ONLY if slug == "volunteer" else PageVisibility.PUBLIC
    page = EditablePage.get_or_create_page(slug, default_visibility=default_vis)

    changed = []
    if payload.content is not None:
        page.content = payload.content
        page.content_html = delta_to_html(payload.content)
        changed.append("content")
    if payload.visibility is not None:
        page.visibility = payload.visibility
        changed.append("visibility")
    page.save()

    audit_log(
        logging.INFO,
        "page_updated",
        request,
        target_type="editable_page",
        target_id=slug,
        details={"slug": slug, "fields_changed": changed},
    )
    return Status(200, _page_out(page))
