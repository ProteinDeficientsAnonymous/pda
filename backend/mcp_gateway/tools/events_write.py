from typing import Annotated, Any

from community._events import create_event as create_event_view
from community._geocode import GeocodeQuery, geocode
from community.models import EventStatus
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from mcp_gateway.event_fields import EventFields, event_summary, to_event_in
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
