from collections.abc import Iterable
from datetime import datetime, timedelta

from community._attendance_analytics import (
    QUALIFYING_EVENT_TYPES,
    QUALIFYING_WINDOW_DAYS,
    MemberAttendanceStats,
)
from community._rsvp_counts import NON_REPORTABLE_EVENT_STATUSES, is_attended, is_didnt_go
from community.models import EventRSVP, EventType
from django.utils import timezone


def user_rsvps_for_attendance(user) -> list[EventRSVP]:
    return list(EventRSVP.objects.filter(user_id=user.id).select_related("event"))


def compute_member_stats(
    rsvps: Iterable[EventRSVP], now: datetime | None = None
) -> MemberAttendanceStats:
    """Row-by-row twin of member_stats_by_user, kept as the parity reference for its SQL."""
    rsvps = list(rsvps)
    window_start = (now or timezone.now()) - timedelta(days=QUALIFYING_WINDOW_DAYS)
    reportable = [r for r in rsvps if r.event.status not in NON_REPORTABLE_EVENT_STATUSES]
    qualifying_dates = [
        r.event.start_datetime
        for r in reportable
        if is_attended(r)
        and r.event.event_type in QUALIFYING_EVENT_TYPES
        and r.event.start_datetime is not None
    ]
    return MemberAttendanceStats(
        last_qualifying_at=max(qualifying_dates, default=None),
        qualifying_count_12mo=sum(1 for d in qualifying_dates if d >= window_start),
        community_count=sum(
            1 for r in reportable if is_attended(r) and r.event.event_type == EventType.COMMUNITY
        ),
        didnt_go_count=sum(1 for r in reportable if is_didnt_go(r)),
        cancel_count=sum(1 for r in rsvps if r.cancelled_at is not None),
    )
