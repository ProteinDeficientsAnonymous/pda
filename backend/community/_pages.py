"""Editable pages endpoints."""

import logging
from datetime import datetime

from config.audit import audit_log
from django.contrib.auth.models import AnonymousUser
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._content_render import render_content_payload
from community._field_limits import FieldLimit
from community._shared import ErrorOut, _optional_jwt
from community._validation import Code, raise_validation
from community.models import EditablePage, PageVisibility

router = Router()


class EditablePageOut(BaseModel):
    slug: str
    content: str
    content_pm: str
    content_html: str
    visibility: str
    updated_at: datetime


class EditablePagePatchIn(BaseModel):
    # Legacy Quill Delta JSON (Flutter). Either content or content_pm.
    content: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    content_pm: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    visibility: str | None = Field(default=None, max_length=FieldLimit.CHOICE)


def _page_out(page: EditablePage) -> EditablePageOut:
    return EditablePageOut(
        slug=page.slug,
        content=page.content,
        content_pm=page.content_pm,
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
            raise_validation(Code.Page.MEMBERS_ONLY, status_code=403)

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
        raise_validation(Code.Perm.DENIED, status_code=403, action="update_page")

    default_vis = PageVisibility.MEMBERS_ONLY if slug == "volunteer" else PageVisibility.PUBLIC
    page = EditablePage.get_or_create_page(slug, default_visibility=default_vis)

    changed = []
    if payload.content is not None or payload.content_pm is not None:
        rendered = render_content_payload(delta=payload.content, prosemirror=payload.content_pm)
        page.content = rendered.content
        page.content_pm = rendered.content_pm
        page.content_html = rendered.content_html
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
