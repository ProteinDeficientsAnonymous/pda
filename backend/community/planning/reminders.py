import logging
from datetime import datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q, QuerySet
from notifications.email_helpers import PlanningEmailVariant

from community.models import AssignmentStatus, SlotAssignment
from community.planning._notify import email_planner, notify_upcoming
from community.planning._planners import planner_users

logger = logging.getLogger(__name__)

# An hour under the cadence so a daily cron that drifts early still sends, but a rerun doesn't.
_REMINDER_GAP = timedelta(days=3) - timedelta(hours=1)
_UPCOMING_LEAD = timedelta(days=42)


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
            user__in=planner_users().exclude(email=""),
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


def send_proposal_reminders(now: datetime) -> int:
    """Email unanswered proposals every 3 days until the month starts; failed sends roll back.

    return(int): number of reminders sent
    """
    sent = 0
    for candidate in list(_due_reminders(now)):
        claimed = _claim(
            _due_reminders(now),
            candidate.pk,
            last_reminded_at=now,
            reminder_count=F("reminder_count") + 1,
        )
        if claimed is None:
            continue
        if email_planner(claimed, PlanningEmailVariant.REMINDER):
            sent += 1
            continue
        SlotAssignment.objects.filter(pk=claimed.pk).update(
            last_reminded_at=claimed.last_reminded_at, reminder_count=claimed.reminder_count
        )
    return sent


def _due_upcoming(now: datetime) -> QuerySet[SlotAssignment]:
    return SlotAssignment.objects.filter(
        _month_not_started(now),
        status=AssignmentStatus.COMMITTED,
        upcoming_notified_at__isnull=True,
        user__in=planner_users(),
    ).select_related("slot__planning_year", "slot__event", "user")


def _in_upcoming_window(assignment: SlotAssignment, now: datetime) -> bool:
    today = now.astimezone(settings.COMMUNITY_TZ).date()
    return assignment.slot.live_event is None and (
        today >= assignment.slot.month_start() - _UPCOMING_LEAD
    )


def send_upcoming_notices(now: datetime) -> int:
    """Tell committed planners their slot is within six weeks of its month and has no event yet.

    If the in-app notice raises, the stamp is rolled back (like a failed reminder) and the batch
    continues; a failed email alone keeps the stamp since the in-app notice already landed.

    return(int): number of planners notified
    """
    sent = 0
    for candidate in list(_due_upcoming(now)):
        if not _in_upcoming_window(candidate, now):
            continue
        claimed = _claim(_due_upcoming(now), candidate.pk, upcoming_notified_at=now)
        if claimed is None:
            continue
        try:
            notify_upcoming(claimed)
        except Exception:  # noqa: BLE001 — one bad notice must not abort the batch
            logger.exception("planning_upcoming_notice_failed", extra={"assignment": claimed.pk})
            SlotAssignment.objects.filter(pk=claimed.pk).update(upcoming_notified_at=None)
            continue
        sent += 1
    return sent
