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
    is_didnt_go,
    reportable_events_q,
)

QUALIFYING_EVENT_TYPES = (EventType.CLUB, EventType.OFFICIAL)
QUALIFYING_WINDOW_DAYS = 365
COMPLIANCE_MIN_COUNT = 2


def _is_reportable(rsvp: EventRSVP) -> bool:
    return rsvp.event.status not in NON_REPORTABLE_EVENT_STATUSES


def _is_qualifying_attended(rsvp: EventRSVP) -> bool:
    return is_attended(rsvp) and rsvp.event.event_type in QUALIFYING_EVENT_TYPES


def qualifying_attendance_q() -> Q:
    """EventRSVP filter matching the rsvps compute_member_stats counts as qualifying.

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
    """compute_member_stats for many users in one grouped query; users with no rsvps are absent."""
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


def compute_member_stats(
    rsvps: Iterable[EventRSVP], now: datetime | None = None
) -> MemberAttendanceStats:
    """Aggregate a member's rsvps into the analytics fields. Pure function over prefetched rows."""
    now = now or timezone.now()
    window_start = now - timedelta(days=QUALIFYING_WINDOW_DAYS)
    reportable_rsvps = [rsvp for rsvp in rsvps if _is_reportable(rsvp)]

    qualifying_dates = [
        rsvp.event.start_datetime for rsvp in reportable_rsvps if _is_qualifying_attended(rsvp)
    ]
    qualifying_dates_known = [d for d in qualifying_dates if d is not None]
    last_qualifying_at = max(qualifying_dates_known) if qualifying_dates_known else None
    qualifying_count_12mo = sum(1 for d in qualifying_dates_known if d >= window_start)

    community_count = sum(
        1
        for rsvp in reportable_rsvps
        if is_attended(rsvp) and rsvp.event.event_type == EventType.COMMUNITY
    )
    didnt_go_count = sum(1 for rsvp in reportable_rsvps if is_didnt_go(rsvp))
    cancel_count = sum(1 for rsvp in rsvps if rsvp.cancelled_at is not None)

    return MemberAttendanceStats(
        last_qualifying_at=last_qualifying_at,
        qualifying_count_12mo=qualifying_count_12mo,
        community_count=community_count,
        didnt_go_count=didnt_go_count,
        cancel_count=cancel_count,
    )


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


def user_rsvps_for_attendance(user) -> list[EventRSVP]:
    """Rsvps for a user, reading the prefetch cache when the caller supplied one."""
    prefetched = getattr(user, "_prefetched_objects_cache", {})
    return (
        list(user.event_rsvps.all())
        if "event_rsvps" in prefetched
        else list(EventRSVP.objects.filter(user_id=user.id).select_related("event"))
    )
