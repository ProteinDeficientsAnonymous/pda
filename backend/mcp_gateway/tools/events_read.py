from typing import Annotated, Any

from asgiref.sync import sync_to_async
from community._event_description_templates import get_event_description_templates
from community._event_list import _hosted_by
from community._event_tags import list_event_tags as list_event_tags_view
from community._events import get_event as get_event_view
from community._tentative_member_access import is_tentative_member, tentative_member_event_q
from community.models import Event, EventStatus
from community.models.event import _is_past_q
from django.db.models import BooleanField, Case, F, Q, When
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


def _my_events(user: User, include_past: bool, limit: int, offset: int) -> list[dict[str, Any]]:
    """Upcoming first, undated (tbd) last, then past newest first; id breaks ties for paging."""
    now = timezone.now()
    active = Q(status=EventStatus.ACTIVE)
    if not include_past:
        active &= ~_is_past_q(now)
    if is_tentative_member(user):
        active &= tentative_member_event_q()
    past = Case(When(_is_past_q(now), then=True), default=False, output_field=BooleanField())
    rows = (
        Event.objects.filter(_hosted_by(user))
        .filter(Q(status=EventStatus.DRAFT) | active)
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
    rows = await sync_to_async(_my_events)(await current_user(), include_past, limit, offset)
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
        "get the official event description templates and their slots. official events start from "
        "official_walk when the event has the 'walk' tag, otherwise official_non_walk. replace each "
        "[ALL CAPS] slot with the planner's details (ask for any you don't know) and keep the rest of "
        "the official copy word for word."
    )
)
async def get_official_event_templates() -> dict[str, Any]:
    templates = await call_view(get_event_description_templates, await current_user())
    return {name: {"text": text, "slots": template_slots(text)} for name, text in templates.items()}
