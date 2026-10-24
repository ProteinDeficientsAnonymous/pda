from datetime import datetime
from typing import Annotated, Any

from community._event_description_templates import get_event_description_templates
from community._event_tags import list_event_tags as list_event_tags_view
from community._events import get_event as get_event_view
from community._events import list_events
from community.models import EventStatus
from pydantic import Field

from mcp_gateway.event_templates import template_slots
from mcp_gateway.server import BASE_URL, current_user, pda_tool
from mcp_gateway.view_calls import call_view

_SUMMARY_FIELDS = (
    *("id", "slug", "title", "status", "event_type", "visibility"),
    *("start_datetime", "end_datetime", "datetime_tbd", "is_past"),
)


def _event_url(event: dict[str, Any]) -> str:
    return f"{BASE_URL}/events/{event['slug'] or event['id']}"


def _summary(event: dict[str, Any]) -> dict[str, Any]:
    tags = [tag["name"] for tag in event["tags"]]
    return {**{key: event[key] for key in _SUMMARY_FIELDS}, "url": _event_url(event), "tags": tags}


def _sort_key(event: dict[str, Any]) -> tuple[bool, float]:
    start = event["start_datetime"]
    when = datetime.fromisoformat(start).timestamp() if start else float("inf")
    return event["is_past"], -when if event["is_past"] else when


@pda_tool(
    description=(
        "list events you host (created or co-host), including your drafts, upcoming first. "
        "use it to find an event's id before reading or editing it."
    )
)
async def list_my_events(
    include_past: Annotated[
        bool, Field(description="also list past published events, newest first after upcoming")
    ] = False,
) -> list[dict[str, Any]]:
    user = await current_user()
    # no start window: the view's window drops undated (TBD) events, which aren't past
    active = await call_view(list_events, user, status=EventStatus.ACTIVE)
    drafts = await call_view(list_events, user, status=EventStatus.DRAFT)
    me = str(user.pk)
    hosted = [
        e
        for e in active
        if (e["created_by_id"] == me or me in e["co_host_ids"])
        and (include_past or not e["is_past"])
    ]
    return sorted((_summary(e) for e in [*drafts, *hosted]), key=_sort_key)


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
        "get the official event description templates and their slots. official events start from "
        "official_walk when the event has the 'walk' tag, otherwise official_non_walk. replace each "
        "[ALL CAPS] slot with the planner's details (ask for any you don't know) and keep the rest of "
        "the official copy word for word."
    )
)
async def get_official_event_templates() -> dict[str, Any]:
    templates = await call_view(get_event_description_templates, await current_user())
    return {name: {"text": text, "slots": template_slots(text)} for name, text in templates.items()}
