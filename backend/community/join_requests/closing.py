import logging

from config.audit import AuditTarget, AuditTargetType, audit_log
from users.models import User

from community.models import JoinRequestEvent, JoinRequestStatus


def close_tentative_requests(request, user: User) -> None:
    """Close the user's tentative join requests so a later check-in can't promote them."""
    actor = getattr(request, "auth", None)
    for join_request in user.join_requests.select_for_update().filter(
        status=JoinRequestStatus.TENTATIVE
    ):
        join_request.save(update_fields=join_request.close(by=actor))
        audit_log(
            logging.INFO,
            "join_request_closed",
            request,
            target=AuditTarget(
                type=AuditTargetType.JOIN_REQUEST,
                id=str(join_request.id),
                details={
                    "event": JoinRequestEvent.CLOSE,
                    "from": JoinRequestStatus.TENTATIVE,
                    "to": JoinRequestStatus.CLOSED,
                    "full_name": join_request.full_name,
                    "user_id": str(user.pk),
                },
            ),
        )
