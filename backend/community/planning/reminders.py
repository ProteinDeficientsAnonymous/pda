import logging
from datetime import date, datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q, QuerySet
from notifications.planning_email import AvailabilityEmailVariant, PlanningEmailVariant
from users.models import HAS_EMAIL

from community.models import AssignmentStatus, PlanningSlot, PlanningYear, SlotAssignment
from community.planning._notify import email_availability, email_planner, notify_upcoming
from community.planning._planners import planner_users

logger = logging.getLogger(__name__)

# An hour under the cadence so a daily cron that drifts early still sends, but a rerun doesn't.
_REMINDER_GAP = timedelta(days=3) - timedelta(hours=1)
_AVAILABILITY_GAP = timedelta(days=7) - timedelta(hours=1)
_UPCOMING_DAYS_OF_DUE_MONTH = (1, 15, 21)
_UPCOMING_DAYS_BEFORE_DUE = (3, 1)


def _month_not_started(now: datetime) -> Q:
    today = now.astimezone(settings.COMMUNITY_TZ).date()
    return Q(slot__planning_year__year__gt=today.year) | Q(
        slot__planning_year__year=today.year, slot__month__gt=today.month
    )


def _due_reminders(now: datetime) -> QuerySet[SlotAssignment]:
    cutoff = now - _REMINDER_GAP
    return (
        SlotAssignment.objects.filter(
            _month_not_started(now),
            status=AssignmentStatus.PROPOSED,
            user__in=planner_users().filter(HAS_EMAIL),
        )
        .filter(
            Q(last_reminded_at__isnull=True, proposed_at__lte=cutoff)
            | Q(last_reminded_at__lte=cutoff)
        )
        .select_related("slot", "user")
    )


def _claim(due: QuerySet[SlotAssignment], pk: UUID, **stamp) -> SlotAssignment | None:
    # Stamping before sending, under a row lock, stops an overlapping run from double-sending.
    with transaction.atomic():
        SlotAssignment.objects.select_for_update(of=("self",)).filter(pk=pk).first()
        claimed = due.filter(pk=pk).first()
        if claimed is not None:
            SlotAssignment.objects.filter(pk=pk).update(**stamp)
        return claimed


def _pending_reminders(now: datetime, user_id: UUID) -> QuerySet[SlotAssignment]:
    return SlotAssignment.objects.filter(
        _month_not_started(now), status=AssignmentStatus.PROPOSED, user_id=user_id
    )


def _claim_planner(now: datetime, user_id: UUID) -> list[SlotAssignment]:
    """Stamp every unanswered slot of a planner who has one due, so they share one cadence.

    return(list[SlotAssignment]): the rows as they were before stamping; empty if none are due
    """
    with transaction.atomic():
        pending = list(
            _pending_reminders(now, user_id)
            .select_for_update(of=("self",))
            .select_related("slot", "user")
            .order_by("slot__planning_year__year", "slot__order")
        )
        if not _due_reminders(now).filter(user_id=user_id).exists():
            return []
        SlotAssignment.objects.filter(pk__in=[a.pk for a in pending]).update(
            last_reminded_at=now, reminder_count=F("reminder_count") + 1
        )
        return pending


def send_proposal_reminders(now: datetime) -> int:
    """Email each planner one reminder listing every unanswered slot, every 3 days until each
    slot's month starts; a failed send rolls the stamps back.

    return(int): number of reminder emails sent
    """
    sent = 0
    due_planners = _due_reminders(now).order_by().values_list("user_id", flat=True).distinct()
    for user_id in list(due_planners):
        claimed = _claim_planner(now, user_id)
        if not claimed:
            continue
        slots = [a.slot for a in claimed]
        if email_planner(claimed[0].user, slots, PlanningEmailVariant.REMINDER):
            sent += 1
            continue
        SlotAssignment.objects.bulk_update(claimed, ["last_reminded_at", "reminder_count"])
    return sent


def _due_upcoming(now: datetime) -> QuerySet[SlotAssignment]:
    return SlotAssignment.objects.filter(
        _month_not_started(now),
        status=AssignmentStatus.COMMITTED,
        user__in=planner_users(),
    ).select_related("slot__planning_year", "slot__event", "user")


def upcoming_stage(slot: PlanningSlot, today: date) -> date | None:
    """return(date | None): the latest notice date on or before today, or None before the first"""
    due = slot.event_due()
    stages = {due.replace(day=day) for day in _UPCOMING_DAYS_OF_DUE_MONTH}
    stages |= {due - timedelta(days=days) for days in _UPCOMING_DAYS_BEFORE_DUE}
    passed = [day for day in stages if due.replace(day=1) <= day < due and day <= today]
    return max(passed, default=None)


def _not_notified_since(stage: date) -> Q:
    stage_start = datetime(stage.year, stage.month, stage.day, tzinfo=settings.COMMUNITY_TZ)
    return Q(upcoming_notified_at__isnull=True) | Q(upcoming_notified_at__lt=stage_start)


def send_upcoming_notices(now: datetime) -> int:
    """Nudge committed planners whose slot has no event on the 1st, 15th and 21st of the month
    it's due and 3 days and 1 day before; a missed run sends only the latest stage.

    If the in-app notice raises, the stamp is rolled back (like a failed reminder) and the batch
    continues; a failed email alone keeps the stamp since the in-app notice already landed.

    return(int): number of planners notified
    """
    today = now.astimezone(settings.COMMUNITY_TZ).date()
    sent = 0
    for candidate in list(_due_upcoming(now)):
        stage = upcoming_stage(candidate.slot, today)
        if stage is None or candidate.slot.live_event is not None:
            continue
        due = _due_upcoming(now).filter(_not_notified_since(stage))
        claimed = _claim(due, candidate.pk, upcoming_notified_at=now)
        if claimed is None:
            continue
        try:
            notify_upcoming(claimed, first=claimed.upcoming_notified_at is None)
        except Exception:
            logger.exception("planning_upcoming_notice_failed", extra={"assignment": claimed.pk})
            SlotAssignment.objects.filter(pk=claimed.pk).update(
                upcoming_notified_at=claimed.upcoming_notified_at
            )
            continue
        sent += 1
    return sent


def _due_availability_years(now: datetime) -> QuerySet[PlanningYear]:
    cutoff = now - _AVAILABILITY_GAP
    today = now.astimezone(settings.COMMUNITY_TZ).date()
    return PlanningYear.objects.filter(
        Q(availability_reminded_at__isnull=True) | Q(availability_reminded_at__lte=cutoff),
        availability_opened_at__lte=cutoff,
        year__gt=today.year,
    )


def send_availability_reminders(now: datetime) -> int:
    """Weekly, email each planner who hasn't filled in an open year's availability, until that
    year starts; the year is stamped under a row lock first so a rerun doesn't double-send.

    return(int): number of reminder emails sent
    """
    sent = 0
    for pk in list(_due_availability_years(now).values_list("pk", flat=True)):
        with transaction.atomic():
            claimed = _due_availability_years(now).select_for_update().filter(pk=pk).first()
            if claimed is None:
                continue
            PlanningYear.objects.filter(pk=pk).update(availability_reminded_at=now)
        waiting = (
            planner_users()
            .filter(HAS_EMAIL)
            .exclude(planning_availabilities__planning_year=claimed)
        )
        for planner in waiting:
            sent += email_availability(planner, claimed.year, AvailabilityEmailVariant.REMINDER)
    return sent
