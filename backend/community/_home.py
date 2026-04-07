"""Home page endpoints."""

import logging
from datetime import datetime

from config.audit import audit_log
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel
from users.permissions import PermissionKey

from community._shared import ErrorOut
from community.models import HomePage

router = Router()


class HomePageOut(BaseModel):
    content: str
    join_content: str
    donate_url: str
    updated_at: datetime


class HomePagePatchIn(BaseModel):
    content: str | None = None
    join_content: str | None = None
    donate_url: str | None = None


@router.get("/home/", response={200: HomePageOut}, auth=None)
def get_home(request):
    h = HomePage.get()
    return Status(
        200,
        HomePageOut(
            content=h.content,
            join_content=h.join_content,
            donate_url=h.donate_url,
            updated_at=h.updated_at,
        ),
    )


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
    changed = []
    if payload.content is not None:
        h.content = payload.content
        changed.append("content")
    if payload.join_content is not None:
        h.join_content = payload.join_content
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
    return Status(
        200,
        HomePageOut(
            content=h.content,
            join_content=h.join_content,
            donate_url=h.donate_url,
            updated_at=h.updated_at,
        ),
    )
