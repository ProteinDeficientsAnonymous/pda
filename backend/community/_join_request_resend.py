"""Re-send magic link for an approved join request that hasn't yet onboarded.

Split from ``_join_requests.py`` to keep that file under the 500-line cap.
"""

import logging
from uuid import UUID

from config.audit import audit_log
from config.ratelimit import rate_limit
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from users.permissions import PermissionKey

from community._join_requests import ApproveJoinRequestOut
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import JoinRequest, JoinRequestStatus

router = Router()


@router.post(
    "/join-requests/{id}/resend-magic-link/",
    response={200: ApproveJoinRequestOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def resend_magic_link(request, id: UUID):
    """Mint a fresh magic-login link for an approved join request whose user
    has not yet onboarded. Lets admins re-share the welcome message when the
    original link was lost. Refuses on already-logged-in users (use the
    members screen's password reset flow for that)."""
    from users._helpers import _create_magic_token
    from users.models import User

    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="join_request",
            target_id=str(id),
            details={
                "endpoint": "resend_magic_link",
                "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="resend_magic_link")

    try:
        join_request = JoinRequest.objects.get(id=id)
    except JoinRequest.DoesNotExist:
        raise_validation(Code.JoinRequest.NOT_FOUND, status_code=404)

    if join_request.status != JoinRequestStatus.APPROVED:
        raise_validation(Code.JoinRequest.NOT_APPROVED, status_code=400)

    user = User.objects.filter(phone_number=join_request.phone_number).first()
    if user is None:
        raise_validation(Code.User.NOT_FOUND, status_code=404)
    if user.archived_at is not None:
        raise_validation(Code.Auth.ACCOUNT_ARCHIVED, status_code=403)
    if user.is_paused:
        raise_validation(Code.Auth.ACCOUNT_PAUSED, status_code=403)
    if not user.needs_onboarding:
        raise_validation(Code.JoinRequest.ALREADY_LOGGED_IN, status_code=400)

    magic_token = _create_magic_token(user)
    audit_log(
        logging.INFO,
        "join_request_magic_link_resent",
        request,
        target_type="join_request",
        target_id=str(join_request.id),
        details={"display_name": join_request.display_name, "user_id": str(user.id)},
    )
    return Status(
        200,
        ApproveJoinRequestOut(
            id=str(join_request.id),
            display_name=join_request.display_name,
            phone_number=join_request.phone_number,
            status=join_request.status,
            magic_link_token=magic_token,
            user_id=str(user.id),
        ),
    )
