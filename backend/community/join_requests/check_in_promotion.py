import logging
from enum import StrEnum

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from notifications.email_helpers import send_member_restored_email
from notifications.email_sender import SendResult, get_email_sender, send_best_effort
from notifications.service import (
    create_check_in_promotion_failed_notifications,
    create_member_restored_notifications,
)
from users.helpers import grant_membership
from users.models import MembershipStatus, User

from community.attendance.analytics import compute_member_stats, is_compliant
from community.join_requests._vetting_email import send_vetting_email
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
    """Promote or restore on check-in; a failure rolls back alone and the check-in stays."""
    was_tentative = user.membership_status == MembershipStatus.TENTATIVE
    try:
        with transaction.atomic():
            return _promote_or_restore(request, user, event)
    except Exception as exc:  # noqa: BLE001 — the attendance mark must survive
        logger.warning("check_in_promotion_failed", exc_info=True)
        audit_log(
            logging.WARNING,
            "check_in_promotion_failed",
            request,
            target=AuditTarget(
                type=AuditTargetType.USER,
                id=str(user.pk),
                details={"event_id": str(event.pk), "error": type(exc).__name__},
            ),
        )
        if was_tentative:
            transaction.on_commit(lambda: notify_vetters_promotion_failed(user, event))
        return None


def _promote_or_restore(request, user: User, event) -> CheckInOutcome | None:
    # Nobody vouches for their own check-in; an archived user comes back only through a vetter.
    if user.pk == request.auth.pk or user.archived_at is not None:
        return None
    if not is_official_or_club(event.event_type):
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
    # Saved before grant_membership: roles on non-members are rejected.
    fields = ["attendance_paused_at", "attendance_grace_notified_at", "restored_at"]
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


def notify_vetters_promotion_failed(user: User, event) -> None:
    """Best-effort vetter alert to approve by hand. A failure must not touch the check-in."""
    name = (user.full_name or user.phone_number).lower()
    message = (
        f"manually approve {name}'s join request — their check-in at"
        f" {event.title.lower()} didn't promote them"
    )
    try:
        create_check_in_promotion_failed_notifications(user, event, message[:255])
    except Exception:  # noqa: BLE001 — the check-in has committed
        logger.warning("check_in_promotion_failed_notifications_failed", exc_info=True)
    send_vetting_email(
        f"check-in promotion failed: {name}",
        f"{message}\n\n{settings.FRONTEND_BASE_URL}/join-requests",
    )
