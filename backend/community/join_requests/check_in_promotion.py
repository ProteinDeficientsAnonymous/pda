import logging
from enum import StrEnum

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.utils import timezone
from users.helpers import grant_membership
from users.models import User

from community.attendance.analytics import compute_member_stats, is_compliant
from community.join_requests.approval import maybe_promote_tentative
from community.models import EventRSVP, is_official_or_club


class CheckInOutcome(StrEnum):
    PROMOTED = "promoted"
    RESTORED = "restored"


def promote_or_restore_on_check_in(request, user: User, event) -> CheckInOutcome | None:
    """Promote a tentative applicant or restore an attendance-paused member on their check-in."""
    # Nobody vouches for their own check-in.
    if user.pk == request.auth.pk or not is_official_or_club(event.event_type):
        return None
    if user.attendance_paused_at is not None:
        return CheckInOutcome.RESTORED if _restore_attendance_paused(request, user) else None
    if maybe_promote_tentative(user, event, request.auth):
        return CheckInOutcome.PROMOTED
    return None


def _restore_attendance_paused(request, user: User) -> bool:
    # Row lock: concurrent check-ins then see each other's marks and only one restores.
    if User.objects.select_for_update().get(pk=user.pk).attendance_paused_at is None:
        return False
    rsvps = EventRSVP.objects.filter(user=user).select_related("event")
    if not is_compliant(compute_member_stats(rsvps)):
        return False

    user.attendance_paused_at = None
    user.attendance_grace_notified_at = None
    user.restored_at = timezone.now()
    user.is_member = True
    # Saved before grant_membership: roles on non-members are rejected.
    fields = ["attendance_paused_at", "attendance_grace_notified_at", "restored_at", "is_member"]
    user.save(update_fields=fields)
    grant_membership(user)
    audit_log(
        logging.WARNING,
        "user_attendance_restored",
        request,
        target=AuditTarget(type=AuditTargetType.USER, id=str(user.pk)),
    )
    return True
