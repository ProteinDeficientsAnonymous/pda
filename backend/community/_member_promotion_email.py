import logging
from datetime import datetime

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community._validation import Code, raise_validation, validate_template_body
from community.models import MemberPromotionEmailTemplate

router = Router()


class MemberPromotionEmailOut(BaseModel):
    body: str
    updated_at: datetime


class MemberPromotionEmailPatchIn(BaseModel):
    body: str | None = Field(default=None)


def _out(obj: MemberPromotionEmailTemplate) -> MemberPromotionEmailOut:
    return MemberPromotionEmailOut(body=obj.body, updated_at=obj.updated_at)


@router.get(
    "/member-promotion-email/",
    response={200: MemberPromotionEmailOut},
    auth=gated_jwt,
)
def get_member_promotion_email(request):
    return Status(200, _out(MemberPromotionEmailTemplate.get()))


@router.patch(
    "/member-promotion-email/",
    response={200: MemberPromotionEmailOut, 403: ErrorOut, 422: ErrorOut},
    auth=gated_jwt,
)
def update_member_promotion_email(request, payload: MemberPromotionEmailPatchIn):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(
                details={
                    "endpoint": "update_member_promotion_email",
                    "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
                }
            ),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="edit_member_promotion_email")

    validate_template_body(
        payload.body,
        required_code=Code.MemberPromotionEmail.BODY_REQUIRED,
        too_long_code=Code.MemberPromotionEmail.BODY_TOO_LONG,
        max_length=FieldLimit.MEMBER_PROMOTION_EMAIL,
    )

    template = MemberPromotionEmailTemplate.get()
    template.body = payload.body
    template.save()
    audit_log(
        logging.INFO,
        "member_promotion_email_updated",
        request,
        target=AuditTarget(type=AuditTargetType.MEMBER_PROMOTION_EMAIL),
    )
    return Status(200, _out(template))
