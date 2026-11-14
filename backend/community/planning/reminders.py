from datetime import datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q, QuerySet
from notifications.email_helpers import PlanningEmailVariant

from community.models import AssignmentStatus, SlotAssignment
from community.planning._notify import email_planner
from community.planning._planners import planner_users

# An hour under the cadence so a daily cron that drifts early still sends, but a rerun doesn't.
_REMINDER_GAP = timedelta(days=3) - timedelta(hours=1)


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
