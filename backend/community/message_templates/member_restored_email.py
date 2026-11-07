import logging

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from users.permissions import PermissionKey

from community.field_limits import FieldLimit
from community.message_templates.member_promotion_email import (
    MemberPromotionEmailOut,
    MemberPromotionEmailPatchIn,
)
from community.models import MemberRestoredEmailTemplate
from community.shared import ErrorOut
from community.validation import Code, raise_validation, validate_template_body

router = Router()


def _out(obj: MemberRestoredEmailTemplate) -> MemberPromotionEmailOut:
    return MemberPromotionEmailOut(body=obj.body, updated_at=obj.updated_at)


@router.get("/member-restored-email/", response={200: MemberPromotionEmailOut}, auth=gated_jwt)
def get_member_restored_email(request):
    return Status(200, _out(MemberRestoredEmailTemplate.get()))


@router.patch(
    "/member-restored-email/",
    response={200: MemberPromotionEmailOut, 403: ErrorOut, 422: ErrorOut},
    auth=gated_jwt,
)
def update_member_restored_email(request, payload: MemberPromotionEmailPatchIn):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        raise_validation(Code.Perm.DENIED, status_code=403, action="edit_member_restored_email")

    validate_template_body(
        payload.body,
        required_code=Code.MemberRestoredEmail.BODY_REQUIRED,
        too_long_code=Code.MemberRestoredEmail.BODY_TOO_LONG,
        max_length=FieldLimit.MEMBER_RESTORED_EMAIL,
    )

    template = MemberRestoredEmailTemplate.get()
    template.body = payload.body
    template.save()
    audit_log(
        logging.INFO,
        "member_restored_email_updated",
        request,
        target=AuditTarget(type=AuditTargetType.MEMBER_RESTORED_EMAIL),
    )
    return Status(200, _out(template))
