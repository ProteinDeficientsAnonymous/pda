import logging
from enum import StrEnum

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.conf import settings
from django.utils import timezone
from notifications.email_helpers import send_member_restored_email
from notifications.email_sender import SendResult, get_email_sender, send_best_effort
from notifications.service import create_member_restored_notifications
from users.helpers import grant_membership
from users.models import MembershipStatus, User

from community.attendance.analytics import compute_member_stats, is_compliant
from community.join_requests.approval import maybe_promote_tentative
from community.models import (
    EventRSVP,
    MemberRestoredEmailTemplate,
    WhatsAppLinkConfig,
    is_official_or_club,
)
from community.shared import render_template_placeholders

logger = logging.getLogger(__name__)


class CheckInOutcome(StrEnum):
    PROMOTED = "promoted"
    RESTORED = "restored"


def promote_or_restore_on_check_in(request, user: User, event) -> CheckInOutcome | None:
    """Promote a tentative applicant or restore an attendance-paused member on their check-in."""
    # Nobody vouches for their own check-in.
    if user.pk == request.auth.pk or not is_official_or_club(event.event_type):
        return None
    if user.membership_status == MembershipStatus.ATTENDANCE_PAUSED:
        return CheckInOutcome.RESTORED if _restore_attendance_paused(request, user) else None
    if maybe_promote_tentative(user, event, request.auth):
        return CheckInOutcome.PROMOTED
    return None


def _restore_attendance_paused(request, user: User) -> bool:
    # Row lock: concurrent check-ins then see each other's marks and only one restores.
    locked = User.objects.select_for_update().get(pk=user.pk)
    if locked.membership_status != MembershipStatus.ATTENDANCE_PAUSED:
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
    user.save(
        update_fields=[
            *fields,
            *user.set_membership_status(MembershipStatus.ACTIVE_MEMBER, by=request.auth),
        ]
    )
    grant_membership(user)
    audit_log(
        logging.WARNING,
        "user_attendance_restored",
        request,
        target=AuditTarget(type=AuditTargetType.USER, id=str(user.pk)),
    )
    return True


def send_member_restored(user: User) -> None:
    """Best-effort restore email. A failure, lookups included, must not roll back the restore."""
    to = user.email
    if not to:
        return

    def send() -> SendResult:
        body = render_template_placeholders(
            MemberRestoredEmailTemplate.get().body,
            {"FIRST_NAME": user.first_name, "WHATSAPP_LINK": WhatsAppLinkConfig.get().link},
        )
        return send_member_restored_email(
            sender=get_email_sender(),
            to=to,
            display_name=user.full_name,
            message_body=body,
            login_url=f"{settings.FRONTEND_BASE_URL}/login",
        )

    send_best_effort(send, "member_restored_email")


def notify_member_restored(user: User) -> None:
    """Best-effort approver notification. A failure must not roll back the restore."""
    try:
        create_member_restored_notifications(user)
    except Exception:  # noqa: BLE001 — the restore has committed
        logger.warning("member_restored_notifications_failed", exc_info=True)
