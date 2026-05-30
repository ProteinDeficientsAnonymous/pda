"""Guidelines and FAQ endpoints."""

import logging
from datetime import datetime

from config.audit import audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._content_render import render_content_payload
from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import FAQ, CommunityGuidelines

router = Router()


class GuidelinesOut(BaseModel):
    content: str
    content_pm: str
    content_html: str
    updated_at: datetime


class GuidelinesPatchIn(BaseModel):
    content_pm: str | None = Field(default=None, max_length=FieldLimit.CONTENT)


def _singleton_out(obj: FAQ | CommunityGuidelines) -> GuidelinesOut:
    return GuidelinesOut(
        content=obj.content,
        content_pm=obj.content_pm,
        content_html=obj.content_html,
        updated_at=obj.updated_at,
    )


def _apply_update(obj: FAQ | CommunityGuidelines, payload: GuidelinesPatchIn) -> None:
    rendered = render_content_payload(prosemirror=payload.content_pm)
    obj.content = rendered.content
    obj.content_pm = rendered.content_pm
    obj.content_html = rendered.content_html
    obj.save()


@router.get("/guidelines/", response={200: GuidelinesOut}, auth=gated_jwt)
def get_guidelines(request):
    return Status(200, _singleton_out(CommunityGuidelines.get()))


@router.patch("/guidelines/", response={200: GuidelinesOut, 403: ErrorOut}, auth=gated_jwt)
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
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_guidelines")
    g = CommunityGuidelines.get()
    _apply_update(g, payload)
    audit_log(
        logging.INFO,
        "guidelines_updated",
        request,
        target_type="guidelines",
        details={"format": "prosemirror"},
    )
    return Status(200, _singleton_out(g))


@router.get("/faq/", response={200: GuidelinesOut}, auth=None)
def get_faq(request):
    return Status(200, _singleton_out(FAQ.get()))


@router.patch("/faq/", response={200: GuidelinesOut, 403: ErrorOut}, auth=gated_jwt)
def update_faq(request, payload: GuidelinesPatchIn):
    if not request.auth.has_permission(PermissionKey.EDIT_FAQ):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={"endpoint": "update_faq", "required_permission": PermissionKey.EDIT_FAQ},
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_guidelines")
    f = FAQ.get()
    _apply_update(f, payload)
    audit_log(
        logging.INFO,
        "faq_updated",
        request,
        target_type="faq",
        details={"format": "prosemirror"},
    )
    return Status(200, _singleton_out(f))
