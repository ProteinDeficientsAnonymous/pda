import json
import logging
from datetime import datetime

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community.field_limits import FieldLimit
from community.models import SpeechTemplate
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()

MAX_OPEN_ROLES = 20
MAX_ROLE_LENGTH = 200
_PM_FIELDS = ("shared_pm", "walk_pm", "restaurant_pm")


class SpeechTemplateOut(BaseModel):
    shared_pm: str
    walk_pm: str
    restaurant_pm: str
    open_roles: list[str]
    updated_at: datetime


class SpeechTemplatePatchIn(BaseModel):
    shared_pm: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    walk_pm: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    restaurant_pm: str | None = Field(default=None, max_length=FieldLimit.CONTENT)
    open_roles: list[str] | None = None


def _out(obj: SpeechTemplate) -> SpeechTemplateOut:
    return SpeechTemplateOut(
        shared_pm=obj.shared_pm,
        walk_pm=obj.walk_pm,
        restaurant_pm=obj.restaurant_pm,
        open_roles=obj.open_roles,
        updated_at=obj.updated_at,
    )


def _validate_pm(field: str, value: str) -> None:
    if not value.strip():
        return
    try:
        doc = json.loads(value)
    except ValueError:
        doc = None
    if not isinstance(doc, dict) or doc.get("type") != "doc":
        raise_validation(Code.SpeechTemplate.INVALID_DOC, field=field)


def _clean_roles(roles: list[str]) -> list[str]:
    cleaned = [r.strip() for r in roles if r.strip()]
    if len(cleaned) > MAX_OPEN_ROLES:
        raise_validation(Code.SpeechTemplate.TOO_MANY_ROLES, field="open_roles", max=MAX_OPEN_ROLES)
    if any(len(r) > MAX_ROLE_LENGTH for r in cleaned):
        raise_validation(Code.SpeechTemplate.ROLE_TOO_LONG, field="open_roles", max=MAX_ROLE_LENGTH)
    return cleaned


@router.get("/speech-template/", response={200: SpeechTemplateOut}, auth=gated_jwt)
def get_speech_template(request):
    return Status(200, _out(SpeechTemplate.get()))


@router.patch("/speech-template/", response={200: SpeechTemplateOut, 403: ErrorOut}, auth=gated_jwt)
def update_speech_template(request, payload: SpeechTemplatePatchIn):
    if not request.auth.has_permission(PermissionKey.EDIT_SPEECH_TEMPLATE):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(
                details={
                    "endpoint": "update_speech_template",
                    "required_permission": PermissionKey.EDIT_SPEECH_TEMPLATE,
                }
            ),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="edit_speech_template")
    template = SpeechTemplate.get()
    changed: list[str] = []
    for field in _PM_FIELDS:
        value = getattr(payload, field)
        if value is not None:
            _validate_pm(field, value)
            setattr(template, field, value)
            changed.append(field)
    if payload.open_roles is not None:
        template.open_roles = _clean_roles(payload.open_roles)
        changed.append("open_roles")
    template.save()
    audit_log(
        logging.INFO,
        "speech_template_updated",
        request,
        target=AuditTarget(type=AuditTargetType.SPEECH_TEMPLATE, details={"fields": changed}),
    )
    return Status(200, _out(template))
