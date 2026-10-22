import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from users.permissions import PermissionKey

from community._join_requests import JoinRequestOut, _join_request_out
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import JoinRequest, JoinRequestStatus

router = Router()


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

    try:
        join_request = JoinRequest.objects.get(id=id)
    except JoinRequest.DoesNotExist:
        raise_validation(Code.JoinRequest.NOT_FOUND, status_code=404)

    if join_request.status != JoinRequestStatus.REJECTED:
        raise_validation(Code.JoinRequest.ONLY_REJECTED_CAN_BE_UN_REJECTED, status_code=400)

    join_request.status = JoinRequestStatus.PENDING
    join_request.rejection_reason = ""
    join_request.rejection_note = ""
    join_request.save(update_fields=["status", "rejection_reason", "rejection_note"])

    audit_log(
        logging.INFO,
        "join_request_unrejected",
        request,
        target=AuditTarget(
            type=AuditTargetType.JOIN_REQUEST,
            id=str(join_request.id),
            details={"full_name": join_request.full_name},
        ),
    )

    return Status(200, _join_request_out(join_request))
