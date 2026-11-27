from collections import defaultdict
from datetime import datetime, timedelta
from typing import Annotated, Any

from asgiref.sync import sync_to_async
from community.events.crud import get_event as get_event_view
from community.events.crud import list_events as list_events_view
from community.events.description_templates import get_event_description_templates
from community.events.listing import EventListQuery, hosted_events_q
from community.events.tags import list_event_tags as list_event_tags_view
from community.models import Event, EventType
from community.models.event import is_past_q
from django.conf import settings
from django.db.models import BooleanField, Case, F, When
from django.utils import timezone
from pydantic import Field
from pydantic_core import to_jsonable_python
from users.models import User

from mcp_gateway.event_templates import template_slots
from mcp_gateway.server import BASE_URL, current_user, pda_tool
from mcp_gateway.view_calls import call_view

_SUMMARY_FIELDS = (
    *("slug", "title", "status", "event_type", "visibility"),
    *("start_datetime", "end_datetime", "datetime_tbd", "is_past"),
)


def _event_url(event: dict[str, Any]) -> str:
    return f"{BASE_URL}/events/{event['slug'] or event['id']}"


def _summary(event: Event) -> dict[str, Any]:
    row = {"id": str(event.id), **{key: getattr(event, key) for key in _SUMMARY_FIELDS}}
    tags = [tag.name for tag in event.tags.all()]
    return {**to_jsonable_python(row), "url": _event_url(row), "tags": tags}


def my_events(user: User, include_past: bool, limit: int, offset: int) -> list[dict[str, Any]]:
    """Upcoming first, undated (tbd) last, then past newest first; id breaks ties for paging."""
    past = Case(
        When(is_past_q(timezone.now()), then=True), default=False, output_field=BooleanField()
    )
    rows = (
        Event.objects.filter(hosted_events_q(user, upcoming=not include_past))
        .annotate(
            listed_past=past,
            upcoming_start=Case(When(listed_past=False, datetime_tbd=False, then="start_datetime")),
            past_start=Case(When(listed_past=True, then="start_datetime")),
        )
        .order_by(
            "listed_past",
            F("upcoming_start").asc(nulls_last=True),
            F("past_start").desc(nulls_first=True),
            "id",
        )
        .prefetch_related("tags")
    )
    return [_summary(e) for e in rows[offset : offset + limit + 1]]


@pda_tool(
    description=(
        "list events you host (created or co-host), including your drafts, upcoming first, "
        "undated (tbd) last. use it to find an event's id before reading or editing it. "
        "results are paged: only fetch the next page (offset=next_offset) if the event you need "
        "isn't on this one."
    )
)
async def list_my_events(
    include_past: Annotated[
        bool, Field(description="also list past published events, newest first after upcoming")
    ] = False,
    limit: Annotated[int, Field(ge=1, le=50, description="events per page")] = 20,
    offset: Annotated[int, Field(ge=0, description="next_offset from the previous page")] = 0,
) -> dict[str, Any]:
    rows = await sync_to_async(my_events)(await current_user(), include_past, limit, offset)
    return {
        "events": rows[:limit],
        "next_offset": offset + limit if len(rows) > limit else None,
    }


@pda_tool(
    description="read one event's full details by id or slug, as the website shows them to you"
)
async def get_event(
    event: Annotated[str, Field(description="event id (uuid) or slug, e.g. from list_my_events")],
) -> dict[str, Any]:
    body = await call_view(get_event_view, await current_user(), event_id=event)
    return {**body, "url": _event_url(body)}


@pda_tool(description="list event tags (id, name, slug) to map a tag name like 'walk' to its id")
async def list_event_tags() -> list[dict[str, Any]]:
    return await call_view(list_event_tags_view, await current_user())


@pda_tool(
    description=(
        "get the official and club event description templates and their slots. official events "
        "start from official_walk when event_format is walk, otherwise official_non_walk; club "
        "events start from club. replace each "
        "[ALL CAPS] slot with the planner's details (ask for any you don't know) and keep the rest of "
        "the official copy word for word."
    )
)
async def get_official_event_templates() -> dict[str, Any]:
    templates = await call_view(get_event_description_templates, await current_user())
    return {name: {"text": text, "slots": template_slots(text)} for name, text in templates.items()}


def _group_name(event: dict[str, Any], clubs: dict[str, str | None]) -> str:
    return clubs.get(event["id"]) or EventType(event["event_type"]).label


def _starts_after(event: dict[str, Any], now: datetime) -> bool:
    return datetime.fromisoformat(event["start_datetime"]) >= now


def _event_lines(event: dict[str, Any]) -> list[str]:
    day = datetime.fromisoformat(event["start_datetime"]).astimezone(settings.COMMUNITY_TZ)
    where = f" @ {event['location']}" if event["location"] else ""
    return [f"{day.month}/{day.day} {event['title']}{where}", _event_url(event)]


def format_upcoming(events: list[dict[str, Any]], clubs: dict[str, str | None]) -> str:
    """One block per club (else event type) in date order: a header, then a date line + url."""
    groups: dict[str, list[str]] = defaultdict(list)
    for event in events:
        groups[_group_name(event, clubs)].extend(_event_lines(event))
    return "\n\n".join("\n".join([name, *lines]) for name, lines in groups.items())


def _club_names(event_ids: list[str]) -> dict[str, str | None]:
    rows = Event.objects.filter(id__in=event_ids).values_list("id", "club__name")
    return {str(event_id): name for event_id, name in rows}


@pda_tool(
    description=(
        "list upcoming dated events you can see, grouped by club (or official / community), "
        "as ready-to-share text: a group name, then 'm/d title @ location' and the event's link. "
        "print the text as is."
    )
)
async def upcoming_events(
    days: Annotated[int, Field(ge=1, le=90, description="how many days ahead to include")] = 14,
) -> str:
    now = timezone.now()
    params = EventListQuery(upcoming=True, end=now + timedelta(days=days))
    listed = await call_view(list_events_view, await current_user(), params=params)
    events = [e for e in listed if not e["datetime_tbd"] and _starts_after(e, now)]
    if not events:
        return f"no upcoming events in the next {days} days"
    clubs = await sync_to_async(_club_names)([e["id"] for e in events])
    return format_upcoming(events, clubs)
