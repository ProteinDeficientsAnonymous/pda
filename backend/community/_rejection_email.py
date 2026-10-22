import logging
from datetime import datetime

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel
from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community._validation import Code, raise_validation, validate_template_body
from community.models import RejectionEmailTemplate, RejectionReason

router = Router()

REASON_TEXT_FIELDS = {
    RejectionReason.VEGETARIAN: "vegetarian_text",
    RejectionReason.NOT_VEGAN: "not_vegan_text",
    RejectionReason.QUESTIONS_NOT_ANSWERED: "questions_not_answered_text",
}


class RejectionEmailOut(BaseModel):
    body: str
    # preset reason key -> the text substituted for ${REASON}
    reasons: dict[str, str]
    updated_at: datetime


class RejectionEmailPatchIn(BaseModel):
    body: str | None = None
    reasons: dict[str, str] | None = None


def _out(obj: RejectionEmailTemplate) -> RejectionEmailOut:
    return RejectionEmailOut(
        body=obj.body,
        reasons={str(key): getattr(obj, field) for key, field in REASON_TEXT_FIELDS.items()},
        updated_at=obj.updated_at,
    )


def _validate_reasons(reasons: dict[str, str]) -> None:
    for key, text in reasons.items():
        if key not in REASON_TEXT_FIELDS:
            raise_validation(
                Code.JoinRequest.INVALID_REJECTION_REASON,
                field="reasons",
                allowed=[str(k) for k in REASON_TEXT_FIELDS],
            )
        validate_template_body(
            text,
            required_code=Code.RejectionEmail.REASON_TEXT_REQUIRED,
            too_long_code=Code.RejectionEmail.REASON_TEXT_TOO_LONG,
            max_length=FieldLimit.REJECTION_REASON_TEXT,
        )


@router.get(
    "/rejection-email/",
    response={200: RejectionEmailOut},
    auth=gated_jwt,
)
def get_rejection_email(request):
    return Status(200, _out(RejectionEmailTemplate.get()))


@router.patch(
    "/rejection-email/",
    response={200: RejectionEmailOut, 403: ErrorOut, 422: ErrorOut},
    auth=gated_jwt,
)
def update_rejection_email(request, payload: RejectionEmailPatchIn):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(
                details={
                    "endpoint": "update_rejection_email",
                    "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
                }
            ),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="edit_rejection_email")

    template = RejectionEmailTemplate.get()
    if payload.body is not None:
        validate_template_body(
            payload.body,
            required_code=Code.RejectionEmail.BODY_REQUIRED,
            too_long_code=Code.RejectionEmail.BODY_TOO_LONG,
            max_length=FieldLimit.REJECTION_EMAIL,
        )
        template.body = payload.body
    if payload.reasons is not None:
        _validate_reasons(payload.reasons)
        for key, text in payload.reasons.items():
            setattr(template, REASON_TEXT_FIELDS[key], text)
    template.save()
    audit_log(
        logging.INFO,
        "rejection_email_updated",
        request,
        target=AuditTarget(type=AuditTargetType.REJECTION_EMAIL),
    )
    return Status(200, _out(template))
