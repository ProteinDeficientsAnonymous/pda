"""Home page endpoints."""

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
from community.models import HomePage

router = Router()


class HomePageOut(BaseModel):
    content: str
    content_pm: str
    content_html: str
    join_content: str
    join_content_pm: str
    join_content_html: str
    donate_url: str
    updated_at: datetime


class HomePagePatchIn(BaseModel):
    # Legacy (Flutter) fields — Quill Delta JSON.
    content: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    join_content: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    # React/TipTap fields — ProseMirror JSON. Either content or content_pm
    # (but not both) should be set per field group.
    content_pm: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    join_content_pm: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    donate_url: str | None = Field(default=None, max_length=FieldLimit.URL)


def _home_out(h: HomePage) -> HomePageOut:
    return HomePageOut(
        content=h.content,
        content_pm=h.content_pm,
        content_html=h.content_html,
        join_content=h.join_content,
        join_content_pm=h.join_content_pm,
        join_content_html=h.join_content_html,
        donate_url=h.donate_url,
        updated_at=h.updated_at,
    )


@router.get("/home/", response={200: HomePageOut}, auth=None)
def get_home(request):
    return Status(200, _home_out(HomePage.get()))


def _apply_content_update(
    h: HomePage,
    *,
    delta: str | None,
    pm: str | None,
    field_prefix: str,
) -> bool:
    """Update one (content, content_pm, content_html) triple. Returns True if changed."""
    if delta is None and pm is None:
        return False
    rendered = render_content_payload(delta=delta, prosemirror=pm)
    setattr(h, field_prefix, rendered.content)
    setattr(h, f"{field_prefix}_pm", rendered.content_pm)
    setattr(h, f"{field_prefix}_html", rendered.content_html)
    return True


@router.patch("/home/", response={200: HomePageOut, 403: ErrorOut}, auth=JWTAuth())
def update_home(request, payload: HomePagePatchIn):
    if not request.auth.has_permission(PermissionKey.EDIT_HOMEPAGE):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={"endpoint": "update_home", "required_permission": PermissionKey.EDIT_HOMEPAGE},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    h = HomePage.get()
    changed: list[str] = []
    if _apply_content_update(
        h, delta=payload.content, pm=payload.content_pm, field_prefix="content"
    ):
        changed.append("content")
    if _apply_content_update(
        h, delta=payload.join_content, pm=payload.join_content_pm, field_prefix="join_content"
    ):
        changed.append("join_content")
    if payload.donate_url is not None:
        h.donate_url = payload.donate_url
        changed.append("donate_url")
    h.save()
    audit_log(
        logging.INFO,
        "homepage_updated",
        request,
        target_type="homepage",
        details={"fields_changed": changed},
    )
    return Status(200, _home_out(h))
