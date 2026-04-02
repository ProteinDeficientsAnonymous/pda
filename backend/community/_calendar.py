"""Calendar feed and token endpoints."""

import secrets
from datetime import timedelta

from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel
from users.models import User as UserModel

from community._events import _can_see_invite_only
from community._shared import ErrorOut  # noqa: F401
from community.models import Event, PageVisibility

router = Router()


class CalendarTokenOut(BaseModel):
    token: str
    feed_url: str


def _build_feed_url(request: HttpRequest, token: str) -> str:
    return request.build_absolute_uri(f"/api/community/calendar/feed/?token={token}")


@router.get("/calendar/token/", response={200: CalendarTokenOut}, auth=JWTAuth())
def get_calendar_token(request):
    user = request.auth
    return Status(
        200,
        CalendarTokenOut(
            token=user.calendar_token,
            feed_url=_build_feed_url(request, user.calendar_token) if user.calendar_token else "",
        ),
    )


@router.post("/calendar/token/", response={200: CalendarTokenOut}, auth=JWTAuth())
def generate_calendar_token(request):
    user = request.auth
    user.calendar_token = secrets.token_urlsafe(32)
    user.save(update_fields=["calendar_token"])
    return Status(
        200,
        CalendarTokenOut(
            token=user.calendar_token,
            feed_url=_build_feed_url(request, user.calendar_token),
        ),
    )


@router.get("/calendar/feed/", auth=None)
def calendar_feed(request, token: str = ""):
    if not token:
        return HttpResponse("Missing token.", status=403, content_type="text/plain")

    try:
        user = UserModel.objects.get(calendar_token=token)
    except UserModel.DoesNotExist:
        return HttpResponse("Invalid token.", status=403, content_type="text/plain")

    # Ignore tokens that are empty strings (not yet generated)
    if not user.calendar_token:
        return HttpResponse("Invalid token.", status=403, content_type="text/plain")

    import icalendar

    cal = icalendar.Calendar()
    cal.add("prodid", "-//PDA//PDA Calendar//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "PDA Events")

    cutoff = timezone.now() - timedelta(days=30)
    events = (
        Event.objects.filter(start_datetime__gte=cutoff)
        .select_related("created_by")
        .prefetch_related("co_hosts", "invited_users")
        .order_by("start_datetime")
    )

    for event in events:
        if event.visibility == PageVisibility.INVITE_ONLY:
            co_host_ids = {str(c.id) for c in event.co_hosts.all()}
            invited_user_ids = {str(u.id) for u in event.invited_users.all()}
            if not _can_see_invite_only(user, co_host_ids, invited_user_ids, event.created_by_id):
                continue
        cal.add_component(_build_vevent(event))

    response = HttpResponse(cal.to_ical(), content_type="text/calendar")
    response["Content-Disposition"] = 'inline; filename="pda-calendar.ics"'
    return response


def _build_vevent(event):
    import icalendar

    vevent = icalendar.Event()
    vevent.add("uid", f"{event.id}@pda")
    vevent.add("dtstamp", timezone.now())
    vevent.add("dtstart", event.start_datetime)
    vevent.add(
        "dtend",
        event.end_datetime or event.start_datetime + timedelta(hours=2),
    )
    vevent.add("summary", event.title)
    desc = _event_ics_description(event)
    if desc:
        vevent.add("description", desc)
    if event.location:
        vevent.add("location", event.location)
    return vevent


def _event_ics_description(event):
    parts = []
    if event.description:
        parts.append(event.description)
    if event.whatsapp_link:
        parts.append(f"WhatsApp: {event.whatsapp_link}")
    if event.partiful_link:
        parts.append(f"Partiful: {event.partiful_link}")
    if event.other_link:
        parts.append(f"Link: {event.other_link}")
    return "\n".join(parts)
