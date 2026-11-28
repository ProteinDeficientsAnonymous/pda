from datetime import date, timedelta
from uuid import UUID

from django.conf import settings
from django.db import transaction
from notifications.email_sender import get_email_sender, send_best_effort
from notifications.models import Notification, NotificationType
from notifications.planning_email import (
    AvailabilityEmailDetails,
    AvailabilityEmailVariant,
    PlanningEmailDetails,
    PlanningEmailVariant,
    describe_slots,
    send_availability_email,
    send_planning_email,
)
from notifications.service import notify_users
from users.helpers import visible_display_name
from users.models import User

from community.models import AssignmentStatus, PlanningSlot, PlanningYear, SlotAssignment
from community.planning._planners import coordinator_users, planner_users


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


def _day_label(day: date) -> str:
    return f"{day:%b} {day.day}".lower()


def email_planner(
    user: User, slots: list[PlanningSlot], variant: PlanningEmailVariant, *, due: date | None = None
) -> bool:
    if not user.email:
        return False
    details = PlanningEmailDetails(
        to=user.email,
        display_name=user.full_name or "",
        slot_labels=tuple(slot.label for slot in slots),
        planning_url=planning_url(),
        variant=variant,
        due_label=_day_label(due) if due else "",
        announce_label=_day_label(due + timedelta(days=1)) if due else "",
    )
    return send_best_effort(
        lambda: send_planning_email(sender=get_email_sender(), details=details),
        f"planning_{variant}_email",
    )


def email_availability(user: User, year: int, variant: AvailabilityEmailVariant) -> bool:
    if not user.email:
        return False
    details = AvailabilityEmailDetails(
        to=user.email,
        display_name=user.full_name or "",
        year=year,
        availability_url=f"{planning_url()}?tab=availability",
        variant=variant,
    )
    return send_best_effort(
        lambda: send_availability_email(sender=get_email_sender(), details=details),
        f"planning_availability_{variant}_email",
    )


def notify_availability_open(planning_year: PlanningYear, opened_by: User) -> None:
    year = planning_year.year
    planners = list(planner_users())
    _notify_many(
        [p.pk for p in planners],
        NotificationType.PLANNING_AVAILABILITY,
        f"when can you plan in {year}? 🌱 tap to fill in your availability",
        opened_by,
    )

    def email_all() -> None:
        for planner in planners:
            email_availability(planner, year, AvailabilityEmailVariant.OPEN)

    transaction.on_commit(email_all)


def notify_proposed(user: User, slots: list[PlanningSlot], proposed_by: User) -> None:
    summary = describe_slots(tuple(slot.label for slot in slots))
    _notify_many(
        [user.pk],
        NotificationType.PLANNING_PROPOSED,
        f"any chance you could plan {summary}? 🌱 tap to answer",
        proposed_by,
    )
    # A rolled-back send must not leave an email out for proposals that are still drafts.
    transaction.on_commit(lambda: email_planner(user, slots, PlanningEmailVariant.PROPOSED))


def notify_confirmed(assignment: SlotAssignment, by: User) -> None:
    name = visible_display_name(by, None).lower()
    _notify(
        assignment,
        NotificationType.PLANNING_COMMITTED,
        f"{name} put you down to plan {assignment.slot.label} 🌱",
        by,
    )
    user, slot = assignment.user, assignment.slot
    transaction.on_commit(lambda: email_planner(user, [slot], PlanningEmailVariant.CONFIRMED))


def notify_upcoming(assignment: SlotAssignment) -> None:
    due = assignment.slot.event_due()
    _notify(
        assignment,
        NotificationType.PLANNING_UPCOMING,
        f"{assignment.slot.label} is coming up — create the event by {_day_label(due)}",
        assignment.proposed_by,
    )
    email_planner(assignment.user, [assignment.slot], PlanningEmailVariant.UPCOMING, due=due)


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
