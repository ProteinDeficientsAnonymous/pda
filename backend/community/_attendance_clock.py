from dataclasses import dataclass
from datetime import date

from dateutil.relativedelta import relativedelta
from django.conf import settings
from users.models import User

from community.models import AttendanceMilestone, AttendanceStatus, EventType
from community.models.event import EventRSVP

QUALIFYING_EVENT_TYPES = (EventType.CLUB, EventType.OFFICIAL)

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
    """Most recent start_datetime of a club/official event the user attended."""
    latest = (
        EventRSVP.objects.filter(
            user=user,
            attendance=AttendanceStatus.ATTENDED,
            event__event_type__in=QUALIFYING_EVENT_TYPES,
        )
        .order_by("-event__start_datetime")
        .values_list("event__start_datetime", flat=True)
        .first()
    )
    return latest.date() if latest else None


def compute_anchor(user: User, today: date) -> date:
    """anchor = max(last qualifying attendance, ATTENDANCE_CLOCK_FLOOR, date_joined)."""
    candidates = [settings.ATTENDANCE_CLOCK_FLOOR, user.date_joined.date()]
    last_attended = last_qualifying_attendance_date(user)
    if last_attended is not None:
        candidates.append(last_attended)
    return max(candidates)


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
