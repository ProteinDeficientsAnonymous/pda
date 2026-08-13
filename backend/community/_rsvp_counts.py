"""RSVP headcount and attendance predicates shared across event surfaces."""

from django.db.models import Case, Count, IntegerField, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce

from community.models import (
    AttendanceStatus,
    Event,
    EventRSVP,
    EventStatus,
    RSVPStatus,
)

# Excluded from attendance surfaces; centralized so report + member-list can't drift.
NON_REPORTABLE_EVENT_STATUSES = (EventStatus.DELETED, EventStatus.CANCELLED, EventStatus.DRAFT)


def reportable_events_q(prefix: str = "event") -> Q:
    """Q excluding non-reportable event statuses across `prefix` (default the event itself)."""
    field = f"{prefix}__status" if prefix else "status"
    return ~Q(**{f"{field}__in": NON_REPORTABLE_EVENT_STATUSES})


def attendance_q(attendance: str, prefix: str = "rsvps") -> Q:
    """Has this attendance mark, regardless of the rsvp's current status.

    attendance(str): the AttendanceStatus to match.
    prefix(str): relation lookup prefix from the queried model to EventRSVP.
    return(Q): filter on attendance=<attendance>.
    """
    return Q(**{f"{prefix}__attendance": attendance})


def no_show_q(prefix: str = "rsvps") -> Q:
    """Was RSVP'd going and didn't go — the narrower, true no-show."""
    return Q(
        **{
            f"{prefix}__status": RSVPStatus.ATTENDING,
            f"{prefix}__attendance": AttendanceStatus.DIDNT_GO,
        }
    )


def going_q(prefix: str = "rsvps") -> Q:
    """Q matching all ATTENDING rsvps across `prefix` (the going denominator)."""
    return Q(**{f"{prefix}__status": RSVPStatus.ATTENDING})


def _plus_one_weight_case(prefix: str = "") -> Case:
    """Case weighting each rsvp as 2 spots when it carries a plus-one, else 1."""
    field = f"{prefix}__has_plus_one" if prefix else "has_plus_one"
    return Case(
        When(**{field: True}, then=Value(2)),
        default=Value(1),
        output_field=IntegerField(),
    )


def going_headcount_expr(prefix: str = "rsvps") -> Coalesce:
    """Sum of ATTENDING spots incl. plus-ones, matching _attending_headcount."""
    return Coalesce(Sum(_plus_one_weight_case(prefix), filter=going_q(prefix)), Value(0))


def _rsvp_headcount_subquery(status: str) -> Subquery:
    return Subquery(
        EventRSVP.objects.filter(event_id=OuterRef("pk"), status=status)
        .order_by()
        .values("event_id")
        .annotate(total=Sum(_plus_one_weight_case()))
        .values("total")[:1],
        output_field=IntegerField(),
    )


def attending_count_annotation() -> Coalesce:
    return Coalesce(_rsvp_headcount_subquery(RSVPStatus.ATTENDING), Value(0))


def waitlisted_count_annotation() -> Coalesce:
    return Coalesce(_rsvp_headcount_subquery(RSVPStatus.WAITLISTED), Value(0))


def invited_count_annotation() -> Coalesce:
    through = Event.invited_users.through
    return Coalesce(
        Subquery(
            through.objects.filter(event_id=OuterRef("pk"))
            .order_by()
            .values("event_id")
            .annotate(total=Count("id"))
            .values("total")[:1],
            output_field=IntegerField(),
        ),
        Value(0),
    )


def is_attended(rsvp: EventRSVP) -> bool:
    """Has an ATTENDED mark, regardless of the rsvp's current status. Shared across event surfaces."""
    return rsvp.attendance == AttendanceStatus.ATTENDED


def is_didnt_go(rsvp: EventRSVP) -> bool:
    """Has a DIDNT_GO mark, regardless of the rsvp's current status. Shared across event surfaces."""
    return rsvp.attendance == AttendanceStatus.DIDNT_GO


def is_no_show(rsvp: EventRSVP) -> bool:
    """Was RSVP'd going and didn't go — the narrower, true no-show. Shared across event surfaces."""
    return rsvp.status == RSVPStatus.ATTENDING and rsvp.attendance == AttendanceStatus.DIDNT_GO


def _attended_count(event: Event) -> int:
    return sum(1 for r in event.rsvps.all() if is_attended(r))


def _didnt_go_count(event: Event) -> int:
    return sum(1 for r in event.rsvps.all() if is_didnt_go(r))


def _no_show_count(event: Event) -> int:
    return sum(1 for r in event.rsvps.all() if is_no_show(r))


def _not_marked_count(event: Event) -> int:
    return sum(
        1
        for r in event.rsvps.all()
        if r.status == RSVPStatus.ATTENDING and r.attendance == AttendanceStatus.UNKNOWN
    )


def _attending_headcount(event: Event) -> int:
    """Count attending spots from prefetched RSVPs (each attendee + their +1)."""
    return sum(
        1 + (1 if r.has_plus_one else 0)
        for r in event.rsvps.all()
        if r.status == RSVPStatus.ATTENDING
    )


def _attending_headcount_db(event: Event, exclude_user=None) -> int:
    """Count attending spots via DB query (use inside select_for_update transactions)."""
    qs = EventRSVP.objects.filter(event=event, status=RSVPStatus.ATTENDING)
    if exclude_user is not None:
        qs = qs.exclude(user=exclude_user)
    result = qs.aggregate(total=Sum(_plus_one_weight_case()))
    return result["total"] or 0


def _waitlisted_count(event: Event) -> int:
    """Count waitlisted spots incl. plus-ones, matching _attending_headcount."""
    return sum(
        1 + (1 if r.has_plus_one else 0)
        for r in event.rsvps.all()
        if r.status == RSVPStatus.WAITLISTED
    )


def _maybe_count(event: Event) -> int:
    return sum(1 for r in event.rsvps.all() if r.status == RSVPStatus.MAYBE)


def _cant_go_count(event: Event) -> int:
    return sum(1 for r in event.rsvps.all() if r.status == RSVPStatus.CANT_GO)


def _no_response_count(event: Event) -> int:
    """Invited users who have no RSVP row."""
    responded = {r.user_id for r in event.rsvps.all()}
    return sum(1 for u in event.invited_users.all() if u.pk not in responded)
