from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.db.models import (
    Case,
    DateTimeField,
    Exists,
    F,
    OuterRef,
    Q,
    QuerySet,
    Value,
    When,
    prefetch_related_objects,
)
from notifications._email_helpers import format_eastern_datetime
from users._helpers import visible_display_name
from users.models import User

from community._rsvp_counts import attending_count_annotation, waitlisted_count_annotation
from community.models import DEFAULT_EVENT_DURATION, Event, EventRSVP, EventStatus, RSVPStatus

_LOOKBACK = timedelta(hours=24)

LABEL_ORDER = ("going", "maybe", "waitlisted", "can't go", "removed")

_STATUS_LABELS: dict[str, str] = {
    RSVPStatus.ATTENDING: "going",
    RSVPStatus.MAYBE: "maybe",
    RSVPStatus.WAITLISTED: "waitlisted",
    RSVPStatus.CANT_GO: "can't go",
    RSVPStatus.REMOVED: "removed",
}

type Window = tuple[datetime, datetime]


@dataclass(frozen=True)
class EventDigest:
    title: str
    when: str
    url: str
    capacity_line: str
    rsvp_groups: list[tuple[str, list[str]]]


@dataclass(frozen=True)
class HostDigest:
    host: User
    events: list[EventDigest]


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


def _when(event: Event) -> str:
    if event.datetime_tbd or event.start_datetime is None:
        return "to be decided"
    return format_eastern_datetime(event.start_datetime)


def _in_window(field: str, window: Window) -> Q:
    start, end = window
    return Q(**{f"{field}__gt": start, f"{field}__lte": end})


def _by_cohost(user_field: str) -> Exists:
    return Exists(
        Event.co_hosts.through.objects.filter(
            event_id=OuterRef("event_id"), user_id=OuterRef(user_field)
        )
    )


def _rsvp_names(
    host: User, event_ids: list[UUID], window: Window
) -> dict[UUID, dict[str, list[str]]]:
    # visible_display_name checks the viewer's admin role on every call.
    prefetch_related_objects([host], "roles")
    rsvps = (
        EventRSVP.objects.filter(_in_window("status_changed_at", window), event_id__in=event_ids)
        .filter(~_by_cohost("user_id"))
        .select_related("user")
        .order_by("status_changed_at", "pk")
    )
    names: dict[UUID, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for rsvp in rsvps:
        label = _STATUS_LABELS[rsvp.status]
        names[rsvp.event_id][label].append(visible_display_name(rsvp.user, host))
    return names


def _event_digest(event: Event, names: dict[str, list[str]]) -> EventDigest:
    return EventDigest(
        title=event.title,
        when=_when(event),
        url=f"{settings.FRONTEND_BASE_URL}/events/{event.slug or event.pk}",
        capacity_line=capacity_line(event),
        rsvp_groups=[(label, names[label]) for label in LABEL_ORDER if names.get(label)],
    )


def build_host_digest(host: User, run_started_at: datetime) -> HostDigest | None:
    events = list(
        eligible_events(run_started_at)
        .filter(co_hosts=host)
        .alias(
            dated_start=Case(
                When(_tbd_q(), then=Value(None)),
                default=F("start_datetime"),
                output_field=DateTimeField(),
            )
        )
        .order_by(F("dated_start").asc(nulls_last=True), "title")
    )
    if not events:
        return None
    window = (host.host_digest_last_sent_at or run_started_at - _LOOKBACK, run_started_at)
    event_ids = [event.pk for event in events]
    names = _rsvp_names(host, event_ids, window)
    digests = [_event_digest(event, names.get(event.pk, {})) for event in events]
    included = [d for d in digests if d.rsvp_groups]
    return HostDigest(host=host, events=included) if included else None
