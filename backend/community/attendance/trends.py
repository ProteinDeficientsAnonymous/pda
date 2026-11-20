from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from django.db.models import Q
from django.utils import timezone
from users.models import MEMBER_OR_ARCHIVED

from community.models import AttendanceStatus, Event, EventRSVP, EventType, RSVPStatus
from community.models.event import is_past_q
from community.rsvps.counts import reportable_events_q

MAX_WINDOW_DAYS = 730


@dataclass
class _Tally:
    events: set[UUID] = field(default_factory=set)
    marked: set[UUID] = field(default_factory=set)
    attended: int = 0
    going: int = 0
    attended_members: set[UUID] = field(default_factory=set)

    def add_rsvp(self, event_id: UUID, user_id: UUID, status: str, marks: tuple, member: bool):
        """marks(tuple): the rsvp's attendance, then its plus-one's when it has one"""
        if any(m != AttendanceStatus.UNKNOWN for m in marks):
            self.marked.add(event_id)
        self.attended += sum(m == AttendanceStatus.ATTENDED for m in marks)
        if member and marks[0] == AttendanceStatus.ATTENDED:
            self.attended_members.add(user_id)
        if status == RSVPStatus.ATTENDING:
            self.going += len(marks)

    def out(self) -> dict[str, Any]:
        marked = len(self.marked)
        return {
            "events": len(self.events),
            "events_without_attendance_marked": len(self.events) - marked,
            "attended": self.attended,
            "unique_attended_members": len(self.attended_members),
            "avg_attended_per_marked_event": round(self.attended / marked, 1) if marked else None,
            "going_headcount": self.going,
        }


def _bucket_key(start: datetime, bucket: str) -> str:
    day = timezone.localtime(start).date()
    if bucket == "month":
        return f"{day:%Y-%m}"
    return (day - timedelta(days=day.weekday())).isoformat()


def _window_q(lo: datetime, now: datetime, prefix: str = "") -> Q:
    return Q(**{f"{prefix}start_datetime__gte": lo}) & is_past_q(now, prefix)


def _tally_window(lo: datetime, now: datetime, bucket: str) -> dict[str, dict[str, _Tally]]:
    tallies: dict[str, dict[str, _Tally]] = {}
    where: dict[UUID, tuple[str, str]] = {}

    def tally(key: str, event_type: str) -> _Tally:
        return tallies.setdefault(key, {t: _Tally() for t in EventType.values})[event_type]

    events = Event.objects.filter(reportable_events_q(""), _window_q(lo, now))
    for event_id, event_type, start in events.values_list("id", "event_type", "start_datetime"):
        where[event_id] = (_bucket_key(start, bucket), event_type)
        for key in (where[event_id][0], "total"):
            tally(key, event_type).events.add(event_id)
    rsvps = EventRSVP.objects.filter(reportable_events_q(), _window_q(lo, now, "event__"))
    for event_id, user_id, status, mark, plus_one, plus_one_mark, membership in rsvps.values_list(
        "event_id",
        "user_id",
        "status",
        "attendance",
        "has_plus_one",
        "plus_one_attendance",
        "user__membership_status",
    ):
        key, event_type = where[event_id]
        marks = (mark, plus_one_mark) if plus_one else (mark,)
        for k in (key, "total"):
            tally(k, event_type).add_rsvp(
                event_id, user_id, status, marks, membership in MEMBER_OR_ARCHIVED
            )
    return tallies


def _render(by_type: dict[str, _Tally]) -> dict[str, dict[str, Any]]:
    return {t: tally.out() for t, tally in by_type.items()}


def event_trends(days: int, bucket: str) -> dict[str, Any]:
    """Counts of events and attendance per bucket and event type.

    days(int): window length, ending now; only events that have ended are counted
    bucket(str): "week" (monday start) or "month"
    return(dict): per-bucket and total tallies by event type
    """
    now = timezone.now()
    lo = now - timedelta(days=days)
    tallies = _tally_window(lo, now, bucket)
    total = tallies.pop("total", None) or {t: _Tally() for t in EventType.values}
    return {
        "window_start": timezone.localtime(lo).date().isoformat(),
        "bucket": bucket,
        "buckets": [{"bucket": k, **_render(v)} for k, v in sorted(tallies.items())],
        "total": _render(total),
    }
