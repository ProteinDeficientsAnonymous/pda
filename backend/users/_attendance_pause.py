from dataclasses import dataclass, field

from community.models import Event, EventType
from community.models.choices import is_official_or_club
from django.db.models import Count, Q

from users._archive import _HELD_RSVP_STATUSES, upcoming_events_q
from users.models import User

QUALIFYING_EVENT_Q = Q(event_type__in=(EventType.OFFICIAL, EventType.CLUB))


@dataclass
class PauseImpact:
    kept_rsvps: list[Event] = field(default_factory=list)
    removed_rsvps: list[Event] = field(default_factory=list)
    kept_hosting: list[Event] = field(default_factory=list)
    removed_hosting: list[Event] = field(default_factory=list)
    drafted_events: list[Event] = field(default_factory=list)


def attendance_pause_impact(user: User) -> PauseImpact:
    """Sort the user's upcoming RSVPs and host spots into what a pause keeps, removes or drafts.

    param(user): the member who would be attendance-paused
    return(PauseImpact): events per bucket, soonest first
    """
    impact = PauseImpact()
    hosted = (
        Event.objects.filter(upcoming_events_q(), pk__in=user.co_hosted_events.values("pk"))
        .annotate(host_count=Count("co_hosts"))
        .order_by("start_datetime")
    )
    for event in hosted:
        if is_official_or_club(event.event_type):
            impact.kept_hosting.append(event)
        elif event.host_count > 1:
            impact.removed_hosting.append(event)
        else:
            impact.drafted_events.append(event)

    # A drafted event loses all its RSVPs, so the user's own isn't listed as removed too.
    rsvped = (
        Event.objects.filter(
            upcoming_events_q(),
            rsvps__user=user,
            rsvps__status__in=_HELD_RSVP_STATUSES,
        )
        .exclude(pk__in=[e.pk for e in impact.drafted_events])
        .order_by("start_datetime")
    )
    for event in rsvped:
        bucket = (
            impact.kept_rsvps if is_official_or_club(event.event_type) else impact.removed_rsvps
        )
        bucket.append(event)
    return impact
