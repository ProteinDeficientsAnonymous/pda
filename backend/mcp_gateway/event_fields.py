from typing import Any

from community._event_schemas import EventIn, EventPatchIn
from community._event_tags import list_event_tags
from community.models import EventType, PageVisibility, is_official_or_club
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field, create_model
from users.models import User

from mcp_gateway.fields import WHEN, NewYorkTime, build, local_time
from mcp_gateway.server import BASE_URL
from mcp_gateway.view_calls import call_view


class EventFields(BaseModel):
    title: str = Field(description="event title")
    description: str = Field("", description="event description shown on the event page")
    start_datetime: NewYorkTime = Field(None, description=f"start, {WHEN}")
    end_datetime: NewYorkTime = Field(None, description=f"end, {WHEN}")
    datetime_tbd: bool = Field(False, description="true when the date/time isn't decided yet")
    location: str = Field("", description="place name and address shown to members")
    latitude: float | None = Field(None, description="meetup point latitude (see find_location)")
    longitude: float | None = Field(None, description="meetup point longitude")
    price: str = Field("", description="free text, e.g. '$15' or '$10-20 sliding scale'")
    venmo_link: str = Field("", description="full link, e.g. https://venmo.com/u/handle")
    cashapp_link: str = Field("", description="full link, e.g. https://cash.app/$cashtag")
    zelle_info: str = Field("", description="zelle email or phone number")
    max_attendees: int | None = Field(None, description="capacity; leave empty for unlimited")
    allow_plus_ones: bool = Field(False, description="not allowed on official or club events")
    rsvp_enabled: bool = Field(False, description="let members rsvp on the site")
    event_type: EventType = Field(EventType.COMMUNITY, description="official/club need permission")
    visibility: PageVisibility = Field(PageVisibility.PUBLIC, description="official/club: public")
    tags: list[str] = Field(default_factory=list, description="existing tag names, e.g. walk")
    whatsapp_link: str = Field("", description="whatsapp group or community invite link")
    partiful_link: str = Field("", description="partiful event link")
    other_link: str = Field("", description="any other link for the event")


async def _tags(names: list[str], user: User) -> dict[str, str]:
    by_name = {tag["name"].lower(): tag for tag in await call_view(list_event_tags, user)}
    unknown = [name for name in names if name.strip().lower() not in by_name]
    if unknown:
        valid = ", ".join(sorted(by_name)) or "none"
        raise ToolError(f"unknown tags: {', '.join(unknown)}. valid tags: {valid}")
    picked = [by_name[name.strip().lower()] for name in names]
    return {tag["name"]: tag["id"] for tag in picked}


def _no_default(schema: dict[str, Any]) -> None:
    schema.pop("default", None)


# Same fields, all optional; an explicit null is only accepted where EventFields allows it.
EventChanges = create_model(
    "EventChanges",
    **{
        name: (
            field.rebuild_annotation(),
            Field(None, description=field.description, json_schema_extra=_no_default),
        )
        for name, field in EventFields.model_fields.items()
    },
)  # ty: ignore[no-matching-overload]


async def to_event_in(fields: EventFields, user: User, **extra: Any) -> EventIn:
    data = fields.model_dump(mode="json", exclude={"tags"})
    tag_ids = list((await _tags(fields.tags, user)).values())
    return build(EventIn, {**data, "tag_ids": tag_ids, **extra})


async def to_event_patch(
    changes: dict[str, Any], user: User, **extra: Any
) -> tuple[EventPatchIn, dict[str, Any]]:
    """return(tuple): the patch, and the changes with tags as their stored names."""
    data = {key: value for key, value in changes.items() if key != "tags"}
    if "tags" in changes:
        tags = await _tags(changes["tags"], user)
        data["tag_ids"] = list(tags.values())
        changes = {**changes, "tags": sorted(tags)}
    return build(EventPatchIn, {**data, **extra}), changes


def event_summary(event: dict[str, Any]) -> dict[str, Any]:
    summary = {key: event[key] for key in EventFields.model_fields if key != "tags"}
    summary["start_datetime"] = local_time(event["start_datetime"])
    summary["end_datetime"] = local_time(event["end_datetime"])
    summary["tags"] = sorted(tag["name"] for tag in event["tags"])
    url = f"{BASE_URL}/events/{event['slug'] or event['id']}"
    return {"id": event["id"], "status": event["status"], "url": url, **summary}


def event_diff(event: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    before = event_summary(event)
    after = {
        key: local_time(value) if key.endswith("_datetime") else value
        for key, value in changes.items()
    }
    return {
        key: {"before": before[key], "after": value}
        for key, value in after.items()
        if before[key] != value
    }


def _plus_ones_note(event: dict[str, Any], changes: dict[str, Any]) -> str | None:
    new_type = changes.get("event_type", event["event_type"])
    plus_ones = changes.get("allow_plus_ones", event["allow_plus_ones"])
    if not (is_official_or_club(new_type) and plus_ones):
        return None
    if new_type != event["event_type"] or not event["allow_plus_ones"]:
        return "plus-ones will be turned off: official and club events don't allow them"
    return None


def _capacity_note(event: dict[str, Any], changes: dict[str, Any]) -> str | None:
    old_max, new_max = event["max_attendees"], changes.get("max_attendees")
    if new_max is None:
        return None
    if (old_max is None or new_max > old_max) and event["waitlisted_count"]:
        return "raising capacity moves waitlisted members to going and emails them"
    going = event["attending_count"]
    if new_max < going:
        return (
            f"{going} spots are already taken, more than the new capacity of {new_max}: "
            "nobody is removed, but new rsvps go to the waitlist"
        )
    return None


def _location_note(event: dict[str, Any], changes: dict[str, Any]) -> str | None:
    moved = changes.get("location", event["location"]) != event["location"]
    repinned = "latitude" in changes or "longitude" in changes
    if moved and not repinned and event["latitude"] is not None:
        return (
            "the map pin stays at the old coordinates: call find_location and send the new "
            "latitude and longitude too"
        )
    return None


def _non_member_note(count: int, removing: bool) -> str | None:
    if not count:
        return None
    note = f"removes {count} non-member rsvp{'s' if count > 1 else ''} and emails them"
    if removing:
        return note
    return f"{note}: ask the user, then preview again with remove_non_member_rsvps true"


def update_notes(
    event: dict[str, Any], changes: dict[str, Any], non_members: int = 0, removing: bool = False
) -> list[str]:
    notes = [
        _plus_ones_note(event, changes),
        _capacity_note(event, changes),
        _location_note(event, changes),
        _non_member_note(non_members, removing),
    ]
    return [note for note in notes if note]
