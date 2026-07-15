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
from community.models import MembershipPromotionMessageTemplate

router = Router()


class MembershipPromotionMessageOut(BaseModel):
    body: str
    updated_at: datetime


class MembershipPromotionMessagePatchIn(BaseModel):
    body: str | None = Field(default=None)


def _out(obj: MembershipPromotionMessageTemplate) -> MembershipPromotionMessageOut:
    return MembershipPromotionMessageOut(body=obj.body, updated_at=obj.updated_at)


@router.get(
    "/membership-promotion-message/",
    response={200: MembershipPromotionMessageOut},
    auth=gated_jwt,
)
def get_membership_promotion_message(request):
    return Status(200, _out(MembershipPromotionMessageTemplate.get()))


@router.patch(
    "/membership-promotion-message/",
    response={200: MembershipPromotionMessageOut, 403: ErrorOut, 422: ErrorOut},
    auth=gated_jwt,
)
def update_membership_promotion_message(request, payload: MembershipPromotionMessagePatchIn):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "update_membership_promotion_message",
                "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
            },
        )
        raise_validation(
            Code.Perm.DENIED, status_code=403, action="edit_membership_promotion_message"
        )

    validate_template_body(
        payload.body,
        required_code=Code.MembershipPromotionMessage.BODY_REQUIRED,
        too_long_code=Code.MembershipPromotionMessage.BODY_TOO_LONG,
        max_length=FieldLimit.MEMBERSHIP_PROMOTION_MESSAGE,
    )

    template = MembershipPromotionMessageTemplate.get()
    template.body = payload.body
    template.save()
    audit_log(
        logging.INFO,
        "membership_promotion_message_updated",
        request,
        target_type="membership_promotion_message",
    )
    return Status(200, _out(template))
