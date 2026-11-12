import logging

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.utils import timezone
from users.models import User

from community.models import JoinRequestStatus


def close_tentative_requests(request, user: User) -> None:
    """Close the user's tentative join requests so a later check-in can't promote them."""
    actor = getattr(request, "auth", None)
    for join_request in user.join_requests.select_for_update().filter(
        status=JoinRequestStatus.TENTATIVE
    ):
        join_request.status = JoinRequestStatus.CLOSED
        join_request.status_changed_at = timezone.now()
        join_request.status_changed_by = actor
        join_request.save(update_fields=["status", "status_changed_at", "status_changed_by"])
        audit_log(
            logging.INFO,
            "join_request_closed",
            request,
            target=AuditTarget(
                type=AuditTargetType.JOIN_REQUEST,
                id=str(join_request.id),
                details={"full_name": join_request.full_name, "user_id": str(user.pk)},
            ),
        )
