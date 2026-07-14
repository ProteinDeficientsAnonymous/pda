"""Tentative-approval confirmation message endpoints.

Plain-text body for the email sent when a tentatively-approved applicant is
promoted to full member. Stored as a singleton (pk=1), same shape as
WelcomeMessageTemplate. Read and edited by users with APPROVE_JOIN_REQUESTS —
the message is part of the approval workflow.
"""

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
from community._validation import Code, raise_validation
from community.models import TentativeApprovalMessageTemplate

router = Router()


class TentativeApprovalMessageOut(BaseModel):
    body: str
    updated_at: datetime


class TentativeApprovalMessagePatchIn(BaseModel):
    body: str | None = Field(default=None)


def _out(obj: TentativeApprovalMessageTemplate) -> TentativeApprovalMessageOut:
    return TentativeApprovalMessageOut(body=obj.body, updated_at=obj.updated_at)


@router.get(
    "/tentative-approval-message/",
    response={200: TentativeApprovalMessageOut},
    auth=gated_jwt,
)
def get_tentative_approval_message(request):
    return Status(200, _out(TentativeApprovalMessageTemplate.get()))


@router.patch(
    "/tentative-approval-message/",
    response={200: TentativeApprovalMessageOut, 403: ErrorOut, 422: ErrorOut},
    auth=gated_jwt,
)
def update_tentative_approval_message(request, payload: TentativeApprovalMessagePatchIn):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "update_tentative_approval_message",
                "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
            },
        )
        raise_validation(
            Code.Perm.DENIED, status_code=403, action="edit_tentative_approval_message"
        )

    if payload.body is None or not payload.body.strip():
        raise_validation(Code.TentativeApprovalMessage.BODY_REQUIRED, field="body")

    if len(payload.body) > FieldLimit.TENTATIVE_APPROVAL_MESSAGE:
        raise_validation(
            Code.TentativeApprovalMessage.BODY_TOO_LONG,
            field="body",
            max_length=FieldLimit.TENTATIVE_APPROVAL_MESSAGE,
        )

    template = TentativeApprovalMessageTemplate.get()
    template.body = payload.body
    template.save()
    audit_log(
        logging.INFO,
        "tentative_approval_message_updated",
        request,
        target_type="tentative_approval_message",
    )
    return Status(200, _out(template))
