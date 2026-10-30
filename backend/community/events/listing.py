from datetime import datetime

from django.db.models import Exists, OuterRef, Prefetch, Q
from django.utils import timezone
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community.events.helpers import (
    _my_rsvp_fields,
    _tags_out,
    _viewer_rsvp_rows,
)
from community.events.schemas import EventListOut
from community.events.tentative_member_access import (
    event_viewer_for,
    is_tentative_member,
    tentative_member_event_q,
)
from community.models import (
    DEFAULT_EVENT_DURATION,
    Event,
    EventRSVP,
    EventStatus,
    PageVisibility,
)
from community.models.event import _is_past_q
from community.rsvps.counts import (
    attending_count_annotation,
    waitlisted_count_annotation,
)
from community.shared import _gated


class EventListQuery(BaseModel):
    status: str = EventStatus.ACTIVE
    start: datetime | None = None
    end: datetime | None = None
    include_imported: bool = True
    hosted: bool = Field(False, description="only events the viewer created or co-hosts")
    upcoming: bool = Field(False, description="drop events that are past; tbd events stay")


def _list_rsvp_prefetch(auth_user):
    """Viewer RSVP only, on `_viewer_rsvps` so `event.rsvps` is not a filtered cache."""
    qs = EventRSVP.objects.none()
    if auth_user is not None:
        qs = EventRSVP.objects.filter(user=auth_user)
    return Prefetch("rsvps", queryset=qs, to_attr="_viewer_rsvps")


def _list_count_annotations():
    return {
        "attending_count": attending_count_annotation(),
        "waitlisted_count": waitlisted_count_annotation(),
    }


def _viewer_is_cohost(auth_user) -> Exists:
    return Exists(
        Event.co_hosts.through.objects.filter(event_id=OuterRef("pk"), user_id=auth_user.pk)
    )


def _viewer_is_invited(auth_user) -> Exists:
    return Exists(
        Event.invited_users.through.objects.filter(event_id=OuterRef("pk"), user_id=auth_user.pk)
    )


def _hosted_by(auth_user):
    return Q(created_by=auth_user) | _viewer_is_cohost(auth_user)


def _status_q(status: str, auth_user, is_authed) -> Q:
    """Status and visibility rules: cancelled and draft rows are the viewer's own."""
    if status in (EventStatus.CANCELLED, EventStatus.DRAFT):
        return Q(status=status) & _hosted_by(auth_user)
    q = Q(status=EventStatus.ACTIVE)
    if not is_authed:
        q &= Q(visibility=PageVisibility.PUBLIC)
    elif is_tentative_member(auth_user):
        q &= tentative_member_event_q()
    return q


def _build_events_queryset(status: str, auth_user, is_authed):
    """Build the events queryset for list_events based on status and auth state."""
    related = ["poll", "tags", _list_rsvp_prefetch(auth_user)]
    if is_authed:
        related.append("co_hosts")
    return (
        Event.objects.prefetch_related(*related)
        .annotate(**_list_count_annotations())
        .filter(_status_q(status, auth_user, is_authed))
    )


def _filter_invite_only(events, auth_user, status: str):
    """Restrict invite-only rows in SQL so list_events never hydrates invitees."""
    if not auth_user or status in (EventStatus.CANCELLED, EventStatus.DRAFT):
        return events
    if auth_user.has_permission(PermissionKey.MANAGE_EVENTS):
        return events
    return events.filter(
        ~Q(visibility=PageVisibility.INVITE_ONLY)
        | Q(created_by=auth_user)
        | _viewer_is_cohost(auth_user)
        | _viewer_is_invited(auth_user)
    )


def _aware(value: datetime) -> datetime:
    return timezone.make_aware(value) if timezone.is_naive(value) else value


def _filter_window(events, start: datetime | None, end: datetime | None, include_imported: bool):
    """Keep events overlapping [start, end); undated (TBD) rows drop out once either bound is set."""
    if not include_imported:
        events = events.filter(is_partiful_import=False, is_legacy=False)
    if start is not None:
        start = _aware(start)
        events = events.filter(
            Q(end_datetime__gte=start)
            | Q(end_datetime__isnull=True, start_datetime__gte=start - DEFAULT_EVENT_DURATION)
        )
    if end is not None:
        events = events.filter(start_datetime__lt=_aware(end))
    return events


def _scope_q(auth_user, hosted: bool, upcoming: bool) -> Q:
    """hosted keeps the viewer's created/co-hosted rows; upcoming drops rows where is_past holds."""
    q = Q()
    if hosted:
        q &= _hosted_by(auth_user)
    if upcoming:
        q &= ~_is_past_q(timezone.now())
    return q


def _filter_scope(events, auth_user, hosted: bool, upcoming: bool):
    return events.filter(_scope_q(auth_user, hosted, upcoming))


def hosted_events_q(auth_user, *, upcoming: bool) -> Q:
    """The viewer's drafts plus list_events' hosted=true rows (invite-only never hides a host)."""
    active = _status_q(EventStatus.ACTIVE, auth_user, True) & _scope_q(auth_user, True, upcoming)
    return _status_q(EventStatus.DRAFT, auth_user, True) | active


def _event_list_out(e, auth_user, is_authed: bool) -> EventListOut:
    auth_user = event_viewer_for(auth_user, e)
    is_authed = is_authed and auth_user is not None
    my_rsvp_status, my_paid_confirmed = _my_rsvp_fields(_viewer_rsvp_rows(e, auth_user), auth_user)
    return EventListOut(
        id=str(e.id),
        slug=e.slug,
        title=e.title,
        description=e.description,
        start_datetime=e.start_datetime,
        end_datetime=e.end_datetime,
        location=_gated(e.location, "", is_authed),
        event_type=e.event_type,
        visibility=e.visibility,
        price=e.price,
        co_host_ids=[str(c.id) for c in e.co_hosts.all()] if is_authed else [],
        datetime_tbd=e.datetime_tbd,
        has_poll=hasattr(e, "poll"),
        allow_plus_ones=e.allow_plus_ones,
        max_attendees=e.max_attendees,
        attending_count=e.attending_count,
        waitlisted_count=e.waitlisted_count,
        my_rsvp=my_rsvp_status,
        my_paid_confirmed=my_paid_confirmed,
        is_past=e.is_past,
        status=e.status,
        is_partiful_import=e.is_partiful_import,
        is_legacy=e.is_legacy,
        tags=_tags_out(e),
    )
