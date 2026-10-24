from typing import Annotated, Any
from uuid import UUID

from community._event_schemas import EventPatchIn
from community._events import create_event as create_event_view
from community._events import get_event as get_event_view
from community._events import update_event as update_event_view
from community._geocode import GeocodeQuery, geocode
from community.models import EventStatus, EventType
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from mcp_gateway.confirm import Confirmed, issue_confirm_token, use_confirm_token
from mcp_gateway.event_fields import EventFields, event_summary, to_event_in
from mcp_gateway.event_templates import template_slots
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.view_calls import call_view


@pda_tool(
    description=(
        "save a new pda event as a draft (only its hosts can see it). before calling: for a walk, "
        "ask for anything missing of the meetup spot, the route (a google maps link) and the food "
        "spot. for an official event, call get_official_event_templates and fill the template's "
        "[ALL CAPS] slots without rewording the rest. after saving, show the user the full summary "
        "and ask whether to publish now (publish_event) or keep it as a draft."
    )
)
async def create_event(fields: EventFields) -> dict[str, Any]:
    user = await current_user()
    payload = await to_event_in(fields, user, status=EventStatus.DRAFT)
    return event_summary(await call_view(create_event_view, user, payload))


def _candidate(feature: dict[str, Any]) -> dict[str, Any]:
    props, (lon, lat) = feature["properties"], feature["geometry"]["coordinates"]
    street = " ".join(filter(None, [props.get("housenumber"), props.get("street")]))
    address = ", ".join(filter(None, [street, props.get("city"), props.get("state")]))
    return {"name": props.get("name") or street, "address": address, "lat": lat, "lon": lon}


@pda_tool(
    description=(
        "look up a place in nyc and return candidates with name, address, lat and lon, to save as "
        "the event's location, latitude and longitude. for official events at a park or other "
        "large open space, ask for the exact meetup spot (a dropped pin, coordinates, or e.g. "
        "'grand army plaza entrance') and save that point, not the park's center. if the user "
        "gives coordinates, use them directly."
    )
)
async def find_location(
    query: Annotated[str, Field(min_length=1, max_length=200, description="place or address")],
) -> list[dict[str, Any]]:
    body = await call_view(geocode, await current_user(), GeocodeQuery(q=query))
    if "features" not in body:
        raise ToolError(body.get("detail", "geocoding service unavailable — try again"))
    return [c for c in map(_candidate, body["features"]) if c["name"]]


EventRef = Annotated[str, Field(description="event id (uuid) or slug, e.g. from list_my_events")]
ConfirmToken = Annotated[
    str | None, Field(description="from the preview; send only after the user said yes")
]


async def _apply(user: Any, event_id: str, payload: EventPatchIn) -> dict[str, Any]:
    body = await call_view(update_event_view, user, event_id=UUID(event_id), payload=payload)
    return event_summary(body)


_BOUND = (
    "photo_updated_at",
    "co_host_ids",
    "invited_user_ids",
    "invite_permission",
    "rsvp_questions",
)


@pda_tool(
    description=(
        "publish a draft so members can see it. the first call returns the event summary plus "
        "confirm_token: show the summary, get an explicit yes, then call again with the token."
    )
)
async def publish_event(event: EventRef, confirm_token: ConfirmToken = None) -> dict[str, Any]:
    user = await current_user()
    body = await call_view(get_event_view, user, event_id=event)
    if body["status"] != EventStatus.DRAFT:
        raise ToolError(f"only drafts can be published; this event is {body['status']}")
    slots = template_slots(body["description"])
    if body["event_type"] == EventType.OFFICIAL and slots:
        raise ToolError(f"fill these template slots in the description first: {', '.join(slots)}")
    summary = event_summary(body)
    # Publishing notifies co-hosts and invitees, so they're part of what the user approves.
    unseen = {key: sorted(body[key]) if key.endswith("_ids") else body[key] for key in _BOUND}
    bound = Confirmed(user.pk, body["id"], "publish", None, [summary, unseen])
    if confirm_token is None:
        return {**summary, "confirm_token": issue_confirm_token(bound)}
    await use_confirm_token(confirm_token, bound)
    return await _apply(user, body["id"], EventPatchIn(status=EventStatus.ACTIVE))
