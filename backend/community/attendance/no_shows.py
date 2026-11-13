from collections import defaultdict
from datetime import datetime
from typing import Self
from uuid import UUID

from django.db.models import Count, F, OuterRef, Q, QuerySet, Subquery, Window
from django.db.models.functions import RowNumber
from django.utils import timezone
from pydantic import BaseModel
from users.models import User

from community.attendance.analytics import qualifying_event_q
from community.models import AttendanceStatus, EventRSVP
from community.rsvps.counts import attendance_q

REPEATED_NO_SHOW_MIN = 3
RECENT_RSVP_LIMIT = 5


class NoShowEventOut(BaseModel):
    event_id: str
    title: str
    start_datetime: datetime


class RsvpOutcomeOut(BaseModel):
    event_id: str
    title: str
    start_datetime: datetime | None = None
    event_type: str
    status: str
    attendance: str

    @classmethod
    def from_rsvp(cls, rsvp: EventRSVP) -> Self:
        event = rsvp.event
        return cls(
            event_id=str(event.id),
            title=event.title,
            start_datetime=event.start_datetime,
            event_type=event.event_type,
            status=rsvp.status,
            attendance=rsvp.attendance,
        )


class RepeatedNoShowOut(BaseModel):
    user_id: str
    full_name: str
    no_show_count: int
    last_no_show: NoShowEventOut
    recent_rsvps: list[RsvpOutcomeOut]


def qualifying_no_show_q(prefix: str = "") -> Q:
    """EventRSVP filter: marked didn't go at a qualifying event.

    prefix(str): relation lookup prefix from the queried model to EventRSVP; "" for EventRSVP.
    return(Q): didn't-go mark at a reportable official or club event with a known start
    """
    event_prefix = f"{prefix}__event" if prefix else "event"
    return attendance_q(AttendanceStatus.DIDNT_GO, prefix=prefix) & qualifying_event_q(event_prefix)


def _latest_no_show(field: str) -> Subquery:
    latest = EventRSVP.objects.filter(qualifying_no_show_q(), user_id=OuterRef("pk")).order_by(
        F("event__start_datetime").desc(), "-pk"
    )
    return Subquery(latest.values(field)[:1])


def _flagged_members(min_no_shows: int) -> QuerySet[User]:
    return (
        User.objects.members()
        .filter(archived_at__isnull=True)
        .annotate(
            no_show_count=Count("event_rsvps", filter=qualifying_no_show_q("event_rsvps")),
            last_no_show_id=_latest_no_show("event_id"),
            last_no_show_title=_latest_no_show("event__title"),
            last_no_show_at=_latest_no_show("event__start_datetime"),
        )
        .filter(no_show_count__gte=min_no_shows)
        .only("first_name", "last_name")
        .order_by("-no_show_count", "-last_no_show_at", "first_name", "last_name", "pk")
    )


def _recent_rsvps(user_ids: list[UUID], now: datetime) -> dict[UUID, list[RsvpOutcomeOut]]:
    newest_first = [F("event__start_datetime").desc(), F("pk").desc()]
    rows = (
        EventRSVP.objects.filter(qualifying_event_q(), user_id__in=user_ids)
        .filter(event__start_datetime__lte=now)
        .select_related("event")
        .annotate(rank=Window(RowNumber(), partition_by=F("user_id"), order_by=newest_first))
        .filter(rank__lte=RECENT_RSVP_LIMIT)
        .order_by("user_id", "rank")
    )
    history: dict[UUID, list[RsvpOutcomeOut]] = defaultdict(list)
    for rsvp in rows:
        history[rsvp.user_id].append(RsvpOutcomeOut.from_rsvp(rsvp))
    return history


def members_with_repeated_no_shows(
    now: datetime | None = None, min_no_shows: int = REPEATED_NO_SHOW_MIN
) -> list[RepeatedNoShowOut]:
    """Unarchived members with min_no_shows+ no-shows at qualifying events, most no-shows first.

    now(datetime | None): cutoff for recent_rsvps, which only lists events already started
    min_no_shows(int): fewest qualifying no-shows that flags a member
    return(list[RepeatedNoShowOut]): two queries regardless of how many members match
    """
    members = list(_flagged_members(min_no_shows))
    history = _recent_rsvps([m.pk for m in members], now or timezone.now()) if members else {}
    return [
        RepeatedNoShowOut(
            user_id=str(m.pk),
            full_name=m.full_name,
            no_show_count=m.no_show_count,
            last_no_show=NoShowEventOut(
                event_id=str(m.last_no_show_id),
                title=m.last_no_show_title,
                start_datetime=m.last_no_show_at,
            ),
            recent_rsvps=history.get(m.pk, []),
        )
        for m in members
    ]
