from dataclasses import dataclass
from datetime import date

from dateutil.relativedelta import relativedelta
from django.conf import settings
from users.models import User

from community._attendance_analytics import QUALIFYING_EVENT_TYPES
from community._rsvp_counts import attendance_q, reportable_events_q
from community.models import AttendanceMilestone, AttendanceStatus, Event

_MILESTONE_OFFSETS: dict[str, relativedelta] = {
    AttendanceMilestone.M10: relativedelta(months=10),
    AttendanceMilestone.M11: relativedelta(months=11),
    AttendanceMilestone.M11_5: relativedelta(months=11, days=15),
    AttendanceMilestone.M12: relativedelta(months=12),
}

# Latest milestone first so "single latest due" picks it first.
_MILESTONES_DESCENDING = [
    AttendanceMilestone.M12,
    AttendanceMilestone.M11_5,
    AttendanceMilestone.M11,
    AttendanceMilestone.M10,
]


def last_qualifying_attendance_date(user: User) -> date | None:
    """Date of compute_member_stats().last_qualifying_at — same rsvps, read via SQL."""
    # One filter() call so the rsvps__ conditions bind to the same rsvp row.
    latest = (
        Event.objects.filter(
            reportable_events_q(prefix=""),
            attendance_q(AttendanceStatus.ATTENDED),
            rsvps__user=user,
            event_type__in=QUALIFYING_EVENT_TYPES,
            start_datetime__isnull=False,
        )
        .order_by("-start_datetime")
        .values_list("start_datetime", flat=True)
        .first()
    )
    return latest.date() if latest else None


def anchor_from(date_joined: date, last_attended: date | None) -> date:
    """anchor = max(last qualifying attendance, ATTENDANCE_CLOCK_FLOOR, date_joined)."""
    candidates = [settings.ATTENDANCE_CLOCK_FLOOR, date_joined]
    if last_attended is not None:
        candidates.append(last_attended)
    return max(candidates)


def compute_anchor(user: User, today: date) -> date:
    return anchor_from(user.date_joined.date(), last_qualifying_attendance_date(user))


def milestone_due_date(anchor: date, milestone: str) -> date:
    return anchor + _MILESTONE_OFFSETS[milestone]


@dataclass(frozen=True)
class DueMilestone:
    milestone: str
    anchor_date: date


def latest_due_milestone(anchor: date, today: date) -> DueMilestone | None:
    """The single latest milestone that has come due for this anchor, if any."""
    for milestone in _MILESTONES_DESCENDING:
        if today >= milestone_due_date(anchor, milestone):
            return DueMilestone(milestone=milestone, anchor_date=anchor)
    return None
