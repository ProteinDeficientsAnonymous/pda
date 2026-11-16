from uuid import UUID

from django.conf import settings
from django.db import transaction
from notifications.email_sender import get_email_sender, send_best_effort
from notifications.models import Notification, NotificationType
from notifications.planning_email import (
    PlanningEmailDetails,
    PlanningEmailVariant,
    describe_slots,
    send_planning_email,
)
from notifications.service import notify_users
from users.helpers import visible_display_name
from users.models import User

from community.models import AssignmentStatus, PlanningSlot, SlotAssignment
from community.planning._planners import coordinator_users


def _notify_many(
    recipient_ids: list[UUID], kind: NotificationType, message: str, related_user: User | None
) -> None:
    # A failed ping must take the rows with it, or the caller's retry duplicates them.
    with transaction.atomic():
        Notification.objects.bulk_create(
            Notification(
                recipient_id=pk, notification_type=kind, related_user=related_user, message=message
            )
            for pk in recipient_ids
        )
        notify_users([str(pk) for pk in recipient_ids])


def _notify(
    assignment: SlotAssignment, kind: NotificationType, message: str, related_user: User | None
) -> None:
    _notify_many([assignment.user_id], kind, message, related_user)


def planning_url() -> str:
    return f"{settings.FRONTEND_BASE_URL}/admin/planning"


def email_planner(user: User, slots: list[PlanningSlot], variant: PlanningEmailVariant) -> bool:
    if not user.email:
        return False
    details = PlanningEmailDetails(
        to=user.email,
        display_name=user.full_name or "",
        slot_labels=tuple(slot.label for slot in slots),
        planning_url=planning_url(),
        variant=variant,
    )
    return send_best_effort(
        lambda: send_planning_email(sender=get_email_sender(), details=details),
        f"planning_{variant}_email",
    )


def notify_proposed(user: User, slots: list[PlanningSlot], proposed_by: User) -> None:
    summary = describe_slots(tuple(slot.label for slot in slots))
    _notify_many(
        [user.pk],
        NotificationType.PLANNING_PROPOSED,
        f"you've been asked to plan {summary} — tap to respond",
        proposed_by,
    )
    email_planner(user, slots, PlanningEmailVariant.PROPOSED)


def notify_upcoming(assignment: SlotAssignment) -> None:
    _notify(
        assignment,
        NotificationType.PLANNING_UPCOMING,
        f"{assignment.slot.label} is coming up — time to create the event",
        assignment.proposed_by,
    )
    email_planner(assignment.user, [assignment.slot], PlanningEmailVariant.UPCOMING)


def notify_withdrawn(assignment: SlotAssignment, by: User) -> None:
    _notify(
        assignment,
        NotificationType.PLANNING_WITHDRAWN,
        f"you're no longer down to plan {assignment.slot.label}",
        by,
    )


def notify_coordinators(assignment: SlotAssignment) -> None:
    planner, slot = assignment.user, assignment.slot
    name = visible_display_name(planner, None).lower()
    kind, message = (
        (NotificationType.PLANNING_COMMITTED, f"{name} is in for {slot.label}")
        if assignment.status == AssignmentStatus.COMMITTED
        else (NotificationType.PLANNING_DECLINED, f"{name} can't do {slot.label}")
    )
    recipients = list(coordinator_users().exclude(pk=planner.pk).values_list("pk", flat=True))
    _notify_many(recipients, kind, message, planner)
