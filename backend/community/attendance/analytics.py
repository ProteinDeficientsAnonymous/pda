"""Compute-on-read attendance aggregates shared by the members analytics
endpoint and join-request attendance history."""

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import NamedTuple
from uuid import UUID

from django.db.models import Count, Max, Q, QuerySet
from django.utils import timezone

from community.models import AttendanceStatus, EventRSVP, EventType
from community.rsvps.counts import (
    NON_REPORTABLE_EVENT_STATUSES,
    attendance_q,
    is_attended,
    reportable_events_q,
)

QUALIFYING_EVENT_TYPES = (EventType.CLUB, EventType.OFFICIAL)
QUALIFYING_WINDOW_DAYS = 365
COMPLIANCE_MIN_COUNT = 2


def _is_reportable(rsvp: EventRSVP) -> bool:
    return rsvp.event.status not in NON_REPORTABLE_EVENT_STATUSES


def qualifying_attendance_q() -> Q:
    """EventRSVP filter matching the rsvps the members analytics counts as qualifying.

    return(Q): reportable, attended, qualifying type, known start
    """
    return (
        attendance_q(AttendanceStatus.ATTENDED, prefix="")
        & reportable_events_q()
        & Q(event__event_type__in=QUALIFYING_EVENT_TYPES, event__start_datetime__isnull=False)
    )


class MemberAttendanceStats(NamedTuple):
    last_qualifying_at: datetime | None
    qualifying_count_12mo: int
    community_count: int
    didnt_go_count: int
    cancel_count: int


EMPTY_MEMBER_STATS = MemberAttendanceStats(None, 0, 0, 0, 0)


def member_stats_by_user(
    users: QuerySet, now: datetime | None = None
) -> dict[UUID, MemberAttendanceStats]:
    """Attendance analytics per user in one grouped query; users with no rsvps are absent."""
    window_start = (now or timezone.now()) - timedelta(days=QUALIFYING_WINDOW_DAYS)
    qualifying = qualifying_attendance_q()
    attended = attendance_q(AttendanceStatus.ATTENDED, prefix="") & reportable_events_q()
    rows = (
        EventRSVP.objects.filter(user__in=users.values("pk"))
        .order_by()
        .values("user_id")
        .annotate(
            last_qualifying_at=Max("event__start_datetime", filter=qualifying),
            qualifying_count_12mo=Count(
                "pk", filter=qualifying & Q(event__start_datetime__gte=window_start)
            ),
            community_count=Count("pk", filter=attended & Q(event__event_type=EventType.COMMUNITY)),
            didnt_go_count=Count(
                "pk",
                filter=attendance_q(AttendanceStatus.DIDNT_GO, prefix="") & reportable_events_q(),
            ),
            cancel_count=Count("pk", filter=Q(cancelled_at__isnull=False)),
        )
    )
    return {row.pop("user_id"): MemberAttendanceStats(**row) for row in rows}


def is_compliant(stats: MemberAttendanceStats) -> bool:
    return stats.qualifying_count_12mo >= COMPLIANCE_MIN_COUNT


def months_since(last_qualifying_at: datetime | None, now: datetime | None = None) -> int | None:
    """Whole months since last_qualifying_at, or None if it never happened."""
    if last_qualifying_at is None:
        return None
    now = now or timezone.now()
    delta = now - last_qualifying_at
    return delta.days // 30


def is_pause_candidate(stats: MemberAttendanceStats) -> bool:
    """No qualifying attendance in the trailing window (or ever). Same window as the compliant count, so the two never disagree."""
    return stats.qualifying_count_12mo == 0


class AttendedEvent(NamedTuple):
    event_id: str
    title: str
    start_datetime: datetime | None
    event_type: str


def attended_events(rsvps: Iterable[EventRSVP]) -> list[AttendedEvent]:
    """All event types, host-marked attended — engagement signal for vetting, oldest first."""
    events = [
        AttendedEvent(
            event_id=str(rsvp.event.id),
            title=rsvp.event.title,
            start_datetime=rsvp.event.start_datetime,
            event_type=rsvp.event.event_type,
        )
        for rsvp in rsvps
        if _is_reportable(rsvp) and is_attended(rsvp)
    ]
    events.sort(key=lambda e: (e.start_datetime is None, e.start_datetime))
    return events
