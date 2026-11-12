"""Calendar feed and token endpoints."""

import secrets
from datetime import timedelta

import icalendar
from config.auth import gated_jwt
from django.conf import settings
from django.db.models import Prefetch, Q
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel
from users.models import CalendarFeedScope
from users.models import User as UserModel

from community.events.helpers import can_see_invite_only, event_co_host_ids
from community.events.read_visibility import enforce_event_read_visibility
from community.models import (
    DEFAULT_EVENT_DURATION,
    Event,
    EventStatus,
    PageVisibility,
    RSVPStatus,
)
from community.shared import authenticated_user, gated, optional_jwt
from community.validation import ValidationException

router = Router()


class CalendarTokenOut(BaseModel):
    token: str
    feed_url: str


def _build_feed_url(request: HttpRequest, token: str) -> str:
    return request.build_absolute_uri(f"/api/community/calendar/feed/?token={token}")


def _rotate_calendar_token(user: UserModel) -> None:
    user.calendar_token = secrets.token_urlsafe(32)
    user.save(update_fields=["calendar_token"])


@router.get("/calendar/token/", response={200: CalendarTokenOut}, auth=gated_jwt)
def get_calendar_token(request):
    user = request.auth
    if not user.calendar_token:
        _rotate_calendar_token(user)
    return Status(
        200,
        CalendarTokenOut(
            token=user.calendar_token,
            feed_url=_build_feed_url(request, user.calendar_token),
        ),
    )


@router.post("/calendar/token/", response={200: CalendarTokenOut}, auth=gated_jwt)
def generate_calendar_token(request):
    user = request.auth
    _rotate_calendar_token(user)
    return Status(
        200,
        CalendarTokenOut(
            token=user.calendar_token,
            feed_url=_build_feed_url(request, user.calendar_token),
        ),
    )


def _feed_events(user: UserModel):
    """Events for a member's subscription feed, after scope and type filters.

    user(UserModel): the feed's subscriber
    return(QuerySet): active, non-TBD events from the last 30 days onward
    """
    cutoff = timezone.now() - timedelta(days=30)
    events = (
        Event.objects.filter(
            start_datetime__gte=cutoff,
            datetime_tbd=False,
            status=EventStatus.ACTIVE,
            is_partiful_import=False,
            is_legacy=False,
        )
        .select_related("created_by")
        .prefetch_related(
            "co_hosts",
            # Only the subscriber's own invite matters for the invite-only check.
            Prefetch("invited_users", queryset=UserModel.objects.filter(pk=user.pk).only("pk")),
        )
        .order_by("start_datetime")
    )

    mine = (
        Q(created_by=user)
        | Q(co_hosts=user)
        | Q(invited_users=user)
        | Q(
            rsvps__user=user,
            rsvps__status__in=[RSVPStatus.ATTENDING, RSVPStatus.MAYBE],
        )
    )

    # own events bypass the type filter
    excluded_types = (
        user.calendar_feed_excluded_types
        if isinstance(user.calendar_feed_excluded_types, list)
        else []
    )
    if excluded_types:
        events = events.exclude(Q(event_type__in=excluded_types) & ~mine).distinct()

    if user.calendar_feed_scope == CalendarFeedScope.MINE:
        events = events.filter(mine).distinct()

    return events


def _feed_user(token: str):
    user = UserModel.objects.filter(calendar_token=token).first()
    # Ignore tokens that are empty strings (not yet generated)
    if user is None or not user.calendar_token:
        return None
    # The feed carries member-only data, so it must stop when site access does.
    if user.archived_at is not None or user.is_guidelines_paused:
        return None
    return user


@router.get("/calendar/feed/", auth=None)
def calendar_feed(request, token: str = ""):
    if not token:
        return HttpResponse("Missing token.", status=403, content_type="text/plain")

    user = _feed_user(token)
    if user is None:
        return HttpResponse("Invalid token.", status=403, content_type="text/plain")

    cal = _new_calendar()
    cal.add("x-wr-calname", "PDA Events")

    for event in _feed_events(user):
        if event.visibility == PageVisibility.INVITE_ONLY:
            co_host_ids = event_co_host_ids(event)
            invited_user_ids = {str(u.id) for u in event.invited_users.all()}
            if not can_see_invite_only(user, co_host_ids, invited_user_ids, event.created_by_id):
                continue
        # The feed is authenticated via the per-user calendar token, so the
        # subscriber is a known member and gets full member-only data.
        cal.add_component(_build_vevent(event, request, is_authed=True))
    cal.add_missing_timezones()

    response = HttpResponse(cal.to_ical(), content_type="text/calendar")
    response["Content-Disposition"] = 'inline; filename="pda-calendar.ics"'
    return response


# Intentionally public ("add to calendar"), but the optional JWT lets an
# authenticated member receive full member-only data while anon callers get
# only the public subset.
@router.get("/events/{event_id}/ics/", auth=optional_jwt)
def single_event_ics(request, event_id: str):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        return HttpResponse("Event not found.", status=404, content_type="text/plain")

    auth_user = authenticated_user(request.auth)
    is_authed = auth_user is not None

    # Apply the canonical event-read visibility rules so the ICS gate stays in
    # lockstep with the main get_event endpoint. This covers deleted (404),
    # draft (403), members-only-non-official-for-anon (404), and invite-only
    # (403) — not just the invite-only tier.
    try:
        enforce_event_read_visibility(event, auth_user)
    except ValidationException as exc:
        return HttpResponse("Event not found.", status=exc.status_code, content_type="text/plain")

    cal = _new_calendar()
    cal.add_component(_build_vevent(event, request, is_authed=is_authed))
    cal.add_missing_timezones()

    response = HttpResponse(cal.to_ical(), content_type="text/calendar")
    response["Content-Disposition"] = f'inline; filename="{_ics_filename(event)}"'
    return response


def _ics_filename(event) -> str:
    """Build a header-safe .ics filename from the event id.

    Uses the opaque event id rather than the (user-controlled) title to avoid
    CR/LF/quote header injection in Content-Disposition.
    """
    return f"event-{event.id}.ics"


def _new_calendar() -> icalendar.Calendar:
    cal = icalendar.Calendar()
    cal.add("prodid", "-//PDA//PDA Calendar//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-timezone", settings.COMMUNITY_TZ.key)
    return cal


def _build_vevent(event, request: HttpRequest, is_authed: bool):
    vevent = icalendar.Event()
    vevent.add("uid", f"{event.id}@pda")
    vevent.add("dtstamp", timezone.now())
    if event.start_datetime:
        # UTC times make iOS Calendar duplicate events in GMT (#1993).
        start = event.start_datetime.astimezone(settings.COMMUNITY_TZ)
        end = event.end_datetime or event.start_datetime + DEFAULT_EVENT_DURATION
        vevent.add("dtstart", start)
        vevent.add("dtend", end.astimezone(settings.COMMUNITY_TZ))
    vevent.add("summary", event.title)
    target_url = request.build_absolute_uri(f"/events/{event.slug or event.id}")
    desc = _event_ics_description(event, target_url, is_authed)
    if desc:
        vevent.add("description", desc)
    location = gated(event.location, "", is_authed)
    if location:
        vevent.add("location", location)
    return vevent


def _event_ics_description(event, target_url: str, is_authed: bool) -> str:
    """Description body for .ics events. The frontend's "add to calendar"
    button has its own builder; both must end with a `View on PDA: <url>`
    line so users can jump back to the event page (#347).

    whatsapp/partiful/other links are member-only and match the gating in
    `event_out` — anon callers never receive them (#445).
    """
    parts = []
    if event.description:
        parts.append(event.description)
    whatsapp = gated(event.whatsapp_link, "", is_authed)
    partiful = gated(event.partiful_link, "", is_authed)
    other = gated(event.other_link, "", is_authed)
    if whatsapp:
        parts.append(f"WhatsApp: {whatsapp}")
    if partiful:
        parts.append(f"Partiful: {partiful}")
    if other:
        parts.append(f"Link: {other}")
    parts.append(f"View on PDA: {target_url}")
    return "\n".join(parts)
