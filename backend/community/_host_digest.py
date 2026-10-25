from datetime import datetime, timedelta

from django.db.models import Exists, OuterRef, Q, QuerySet
from users.models import User

from community._rsvp_counts import attending_count_annotation, waitlisted_count_annotation
from community.models import DEFAULT_EVENT_DURATION, Event, EventStatus

_LOOKBACK = timedelta(hours=24)


def _tbd_q() -> Q:
    return Q(datetime_tbd=True) | Q(start_datetime__isnull=True)


def _eligible(run_started_at: datetime) -> QuerySet[Event]:
    cutoff = run_started_at - _LOOKBACK
    not_long_over = Q(end_datetime__gte=cutoff) | Q(
        end_datetime__isnull=True, start_datetime__gte=cutoff - DEFAULT_EVENT_DURATION
    )
    return Event.objects.filter(
        _tbd_q() | not_long_over,
        status=EventStatus.ACTIVE,
        deleted_at__isnull=True,
        rsvp_enabled=True,
    )


def eligible_events(run_started_at: datetime) -> QuerySet[Event]:
    return _eligible(run_started_at).annotate(
        attending_count=attending_count_annotation(),
        waitlisted_count=waitlisted_count_annotation(),
    )


def digest_recipients(run_started_at: datetime) -> QuerySet[User]:
    hosts_eligible_event = Exists(_eligible(run_started_at).filter(co_hosts=OuterRef("pk")))
    return (
        User.objects.active_members()
        .filter(hosts_eligible_event, email__isnull=False, host_digest_opt_out=False)
        .exclude(email="")
    )


def capacity_line(event: Event) -> str:
    attending, waitlisted = event.attending_count, event.waitlisted_count
    cap = event.max_attendees
    if cap is None:
        line = f"{attending} going"
    else:
        line = f"{attending}/{cap} going" + (" · full" if attending >= cap else "")
    if waitlisted > 0:
        line += f" · {waitlisted} waitlisted"
    return line
