import logging
from datetime import datetime

from config.audit import audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community._validation import Code, raise_validation, validate_template_body
from community.models import MemberPromotionMessageTemplate

router = Router()


class MemberPromotionMessageOut(BaseModel):
    body: str
    updated_at: datetime


class MemberPromotionMessagePatchIn(BaseModel):
    body: str | None = Field(default=None)


def _out(obj: MemberPromotionMessageTemplate) -> MemberPromotionMessageOut:
    return MemberPromotionMessageOut(body=obj.body, updated_at=obj.updated_at)


@router.get(
    "/member-promotion-message/",
    response={200: MemberPromotionMessageOut},
    auth=gated_jwt,
)
def get_member_promotion_message(request):
    return Status(200, _out(MemberPromotionMessageTemplate.get()))


@router.patch(
    "/member-promotion-message/",
    response={200: MemberPromotionMessageOut, 403: ErrorOut, 422: ErrorOut},
    auth=gated_jwt,
)
def update_member_promotion_message(request, payload: MemberPromotionMessagePatchIn):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "update_member_promotion_message",
                "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="edit_member_promotion_message")

    validate_template_body(
        payload.body,
        required_code=Code.MemberPromotionMessage.BODY_REQUIRED,
        too_long_code=Code.MemberPromotionMessage.BODY_TOO_LONG,
        max_length=FieldLimit.MEMBER_PROMOTION_MESSAGE,
    )

    template = MemberPromotionMessageTemplate.get()
    template.body = payload.body
    template.save()
    audit_log(
        logging.INFO,
        "member_promotion_message_updated",
        request,
        target_type="member_promotion_message",
    )
    return Status(200, _out(template))
