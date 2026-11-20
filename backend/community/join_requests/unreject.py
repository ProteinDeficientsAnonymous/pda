import logging
from typing import NoReturn
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from django.db import IntegrityError, transaction
from ninja import Router
from ninja.responses import Status
from users.permissions import PermissionKey

from community.join_requests.approval import applicant_user
from community.join_requests.manage import JoinRequestOut, join_request_out
from community.models import (
    OPEN_JOIN_REQUEST_STATUSES,
    JoinRequest,
    JoinRequestEvent,
    JoinRequestStatus,
)
from community.shared import ErrorOut
from community.validation import Code, InvalidStateTransition, TransitionFailure, raise_validation

router = Router()


def _raise_open_request_exists(join_request: JoinRequest, before_status: str) -> NoReturn:
    raise InvalidStateTransition(
        Code.JoinRequest.OPEN_REQUEST_EXISTS,
        TransitionFailure(
            action="join_request_transition_rejected",
            target_type=AuditTargetType.JOIN_REQUEST,
            target_id=str(join_request.id),
            event=JoinRequestEvent.UNREJECT,
            from_status=before_status,
            to_status=JoinRequestStatus.PENDING,
            extra={"full_name": join_request.full_name},
        ),
    )


@router.patch(
    "/join-requests/{id}/unreject/",
    response={200: JoinRequestOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def unreject_join_request(request, id: UUID):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(
                type=AuditTargetType.JOIN_REQUEST,
                id=str(id),
                details={
                    "endpoint": "unreject_join_request",
                    "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
                },
            ),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="unreject_join_request")

    with transaction.atomic():
        try:
            join_request = JoinRequest.objects.select_for_update().get(id=id)
        except JoinRequest.DoesNotExist:
            raise_validation(Code.JoinRequest.NOT_FOUND, status_code=404)

        before_status = str(join_request.status)
        fields = join_request.unreject(by=request.auth)
        if JoinRequest.objects.filter(
            phone_number=join_request.phone_number,
            status__in=OPEN_JOIN_REQUEST_STATUSES,
        ).exists():
            _raise_open_request_exists(join_request, before_status)
        # Only this row is locked; a concurrent unreject or submit for the phone trips the constraint.
        try:
            with transaction.atomic():
                join_request.save(update_fields=fields)
        except IntegrityError:
            _raise_open_request_exists(join_request, before_status)

    user = applicant_user(join_request)
    audit_log(
        logging.INFO,
        "join_request_unrejected",
        request,
        target=AuditTarget(
            type=AuditTargetType.JOIN_REQUEST,
            id=str(join_request.id),
            details={
                "event": JoinRequestEvent.UNREJECT,
                "from": before_status,
                "to": JoinRequestStatus.PENDING,
                "full_name": join_request.full_name,
                "user_id": str(user.pk) if user else None,
            },
        ),
    )

    return Status(200, join_request_out(join_request))
