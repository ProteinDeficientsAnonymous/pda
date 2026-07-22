"""Compute-on-read attendance aggregates shared by the members analytics
endpoint and join-request attendance history."""

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import NamedTuple

from django.db.models import Prefetch
from django.utils import timezone

from community._rsvp_counts import NON_REPORTABLE_EVENT_STATUSES
from community.models import AttendanceStatus, EventRSVP, EventType, RSVPStatus

QUALIFYING_EVENT_TYPES = (EventType.CLUB, EventType.OFFICIAL)
QUALIFYING_WINDOW_DAYS = 365
COMPLIANCE_MIN_COUNT = 2


def _is_reportable(rsvp: EventRSVP) -> bool:
    return rsvp.event.status not in NON_REPORTABLE_EVENT_STATUSES


def _is_marked(rsvp: EventRSVP, attendance: str) -> bool:
    """Attendance mark gated on status=ATTENDING, so a stranded mark left after
    the rsvp flips to CANT_GO/removed isn't counted. Mirrors attendance_q."""
    return (
        _is_reportable(rsvp)
        and rsvp.status == RSVPStatus.ATTENDING
        and rsvp.attendance == attendance
    )


def _is_qualifying_attended(rsvp: EventRSVP) -> bool:
    return (
        _is_marked(rsvp, AttendanceStatus.ATTENDED)
        and rsvp.event.event_type in QUALIFYING_EVENT_TYPES
    )


class MemberAttendanceStats(NamedTuple):
    last_qualifying_at: datetime | None
    qualifying_count_12mo: int
    community_count: int
    no_show_count: int
    cancel_count: int


def member_rsvps_prefetch() -> Prefetch:
    """Prefetch for annotating a User queryset with rsvps + events, ready for compute_member_stats."""
    return Prefetch("event_rsvps", queryset=EventRSVP.objects.select_related("event"))


def compute_member_stats(
    rsvps: Iterable[EventRSVP], now: datetime | None = None
) -> MemberAttendanceStats:
    """Aggregate a member's rsvps into the analytics fields. Pure function over prefetched rows."""
    now = now or timezone.now()
    window_start = now - timedelta(days=QUALIFYING_WINDOW_DAYS)

    qualifying_dates = [
        rsvp.event.start_datetime for rsvp in rsvps if _is_qualifying_attended(rsvp)
    ]
    qualifying_dates_known = [d for d in qualifying_dates if d is not None]
    last_qualifying_at = max(qualifying_dates_known) if qualifying_dates_known else None
    qualifying_count_12mo = sum(1 for d in qualifying_dates_known if d >= window_start)

    community_count = sum(
        1
        for rsvp in rsvps
        if _is_marked(rsvp, AttendanceStatus.ATTENDED)
        and rsvp.event.event_type == EventType.COMMUNITY
    )
    no_show_count = sum(1 for rsvp in rsvps if _is_marked(rsvp, AttendanceStatus.NO_SHOW))
    cancel_count = sum(1 for rsvp in rsvps if rsvp.cancelled_at is not None)

    return MemberAttendanceStats(
        last_qualifying_at=last_qualifying_at,
        qualifying_count_12mo=qualifying_count_12mo,
        community_count=community_count,
        no_show_count=no_show_count,
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
        if _is_marked(rsvp, AttendanceStatus.ATTENDED)
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


def resolve_join_request_user(join_request):
    """JoinRequest.user FK when set, else a unique phone_number match against guest users."""
    if join_request.user_id:
        return join_request.user
    from users.models import User

    return User.objects.filter(is_member=False, phone_number=join_request.phone_number).first()
