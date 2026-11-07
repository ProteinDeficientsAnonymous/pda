import logging
from datetime import timedelta
from enum import StrEnum

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.conf import settings
from django.utils import timezone
from notifications.email_helpers import send_member_restored_email
from notifications.email_sender import get_email_sender, send_best_effort
from notifications.service import create_member_restored_notifications
from users.helpers import grant_membership
from users.models import User

from community.attendance.analytics import (
    COMPLIANCE_MIN_COUNT,
    QUALIFYING_WINDOW_DAYS,
    qualifying_attendance_q,
)
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


def maybe_promote_non_member(request, user: User, event) -> CheckInOutcome | None:
    """Promote a tentative applicant or restore an attendance-paused member on their check-in."""
    # A host marking their own attendance can't vouch for themselves.
    if user.pk == request.auth.pk or not is_official_or_club(event.event_type):
        return None
    # Checked first so a stale TENTATIVE request can't promote a paused member on one check-in.
    if user.attendance_paused_at is not None:
        return CheckInOutcome.RESTORED if _restore_attendance_paused(request, user) else None
    if maybe_promote_tentative(user, event, request.auth):
        return CheckInOutcome.PROMOTED
    return None


def _restore_attendance_paused(request, user: User) -> bool:
    now = timezone.now()
    qualifying_count = EventRSVP.objects.filter(
        qualifying_attendance_q(),
        user=user,
        event__start_datetime__gte=now - timedelta(days=QUALIFYING_WINDOW_DAYS),
    ).count()
    if qualifying_count < COMPLIANCE_MIN_COUNT:
        return False

    user.attendance_paused_at = None
    user.attendance_grace_notified_at = None
    user.restored_at = now
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


def send_member_restored(user: User) -> None:
    """Best-effort restore email. A send failure must not roll back the restore."""
    if not user.email:
        return
    body = render_template_placeholders(
        MemberRestoredEmailTemplate.get().body,
        {"FIRST_NAME": user.first_name, "WHATSAPP_LINK": WhatsAppLinkConfig.get().link},
    )
    send_best_effort(
        lambda: send_member_restored_email(
            sender=get_email_sender(),
            to=user.email or "",
            display_name=user.full_name,
            message_body=body,
            login_url=f"{settings.FRONTEND_BASE_URL}/login",
        ),
        "member_restored_email",
    )


def notify_member_restored(user: User) -> None:
    """Best-effort approver notification. A failure must not roll back the restore."""
    try:
        create_member_restored_notifications(user)
    except Exception:  # noqa: BLE001 — the restore has committed
        logger.warning("member_restored_notifications_failed", exc_info=True)
