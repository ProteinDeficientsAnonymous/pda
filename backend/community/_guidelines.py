"""Guidelines and FAQ endpoints."""

import logging
from datetime import datetime

from config.audit import audit_log
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel
from users.permissions import PermissionKey

from community._delta_html import delta_to_html
from community._shared import ErrorOut
from community.models import FAQ, CommunityGuidelines

router = Router()


class GuidelinesOut(BaseModel):
    content: str
    content_html: str
    updated_at: datetime


class GuidelinesPatchIn(BaseModel):
    content: str


@router.get("/guidelines/", response={200: GuidelinesOut}, auth=JWTAuth())
def get_guidelines(request):
    g = CommunityGuidelines.get()
    return Status(
        200, GuidelinesOut(content=g.content, content_html=g.content_html, updated_at=g.updated_at)
    )


@router.patch("/guidelines/", response={200: GuidelinesOut, 403: ErrorOut}, auth=JWTAuth())
def update_guidelines(request, payload: GuidelinesPatchIn):
    if not request.auth.has_permission(PermissionKey.EDIT_GUIDELINES):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "update_guidelines",
                "required_permission": PermissionKey.EDIT_GUIDELINES,
            },
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    g = CommunityGuidelines.get()
    g.content = payload.content
    g.content_html = delta_to_html(payload.content)
    g.save()
    audit_log(
        logging.INFO,
        "guidelines_updated",
        request,
        target_type="guidelines",
        details={"content_length": len(payload.content)},
    )
    return Status(
        200, GuidelinesOut(content=g.content, content_html=g.content_html, updated_at=g.updated_at)
    )


@router.get("/faq/", response={200: GuidelinesOut}, auth=None)
def get_faq(request):
    f = FAQ.get()
    return Status(
        200, GuidelinesOut(content=f.content, content_html=f.content_html, updated_at=f.updated_at)
    )


@router.patch("/faq/", response={200: GuidelinesOut, 403: ErrorOut}, auth=JWTAuth())
def update_faq(request, payload: GuidelinesPatchIn):
    if not request.auth.has_permission(PermissionKey.EDIT_FAQ):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={"endpoint": "update_faq", "required_permission": PermissionKey.EDIT_FAQ},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    f = FAQ.get()
    f.content = payload.content
    f.content_html = delta_to_html(payload.content)
    f.save()
    audit_log(
        logging.INFO,
        "faq_updated",
        request,
        target_type="faq",
        details={"content_length": len(payload.content)},
    )
    return Status(
        200, GuidelinesOut(content=f.content, content_html=f.content_html, updated_at=f.updated_at)
    )
