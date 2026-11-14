from django.conf import settings
from notifications.email_helpers import PlanningProposedEmailDetails, send_planning_proposed_email
from notifications.email_sender import get_email_sender, send_best_effort
from notifications.models import Notification, NotificationType
from notifications.service import notify_users

from community.models import SlotAssignment


def _notify(assignment: SlotAssignment, kind: NotificationType, message: str) -> None:
    Notification.objects.create(
        recipient_id=assignment.user_id,
        notification_type=kind,
        related_user=assignment.proposed_by,
        message=message,
    )
    notify_users([str(assignment.user_id)])


def notify_proposed(assignment: SlotAssignment) -> None:
    slot, user = assignment.slot, assignment.user
    _notify(
        assignment,
        NotificationType.PLANNING_PROPOSED,
        f"you've been asked to plan {slot.label} — tap to respond",
    )
    if not user.email:
        return
    details = PlanningProposedEmailDetails(
        to=user.email,
        display_name=user.full_name or "",
        slot_label=slot.label,
        planning_url=f"{settings.FRONTEND_BASE_URL}/admin/planning",
    )
    send_best_effort(
        lambda: send_planning_proposed_email(sender=get_email_sender(), details=details),
        "planning_proposed_email",
    )


def notify_withdrawn(assignment: SlotAssignment) -> None:
    _notify(
        assignment,
        NotificationType.PLANNING_WITHDRAWN,
        f"you're no longer down to plan {assignment.slot.label}",
    )
