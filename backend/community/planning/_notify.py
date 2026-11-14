from uuid import UUID

from django.conf import settings
from notifications.email_helpers import PlanningProposedEmailDetails, send_planning_proposed_email
from notifications.email_sender import get_email_sender, send_best_effort
from notifications.models import Notification, NotificationType
from notifications.service import notify_users
from users.helpers import visible_display_name
from users.models import User

from community.models import SlotAssignment
from community.planning._planners import coordinator_users


def _notify_many(
    recipient_ids: list[UUID], kind: NotificationType, message: str, related_user: User | None
) -> None:
    Notification.objects.bulk_create(
        Notification(
            recipient_id=pk, notification_type=kind, related_user=related_user, message=message
        )
        for pk in recipient_ids
    )
    notify_users([str(pk) for pk in recipient_ids])


def _notify(assignment: SlotAssignment, kind: NotificationType, message: str) -> None:
    _notify_many([assignment.user_id], kind, message, assignment.proposed_by)


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


def notify_coordinators(assignment: SlotAssignment, committed: bool) -> None:
    planner, slot = assignment.user, assignment.slot
    name = visible_display_name(planner, None).lower()
    kind, message = (
        (NotificationType.PLANNING_COMMITTED, f"{name} is in for {slot.label}")
        if committed
        else (NotificationType.PLANNING_DECLINED, f"{name} can't do {slot.label}")
    )
    recipients = list(coordinator_users().exclude(pk=planner.pk).values_list("pk", flat=True))
    _notify_many(recipients, kind, message, planner)
