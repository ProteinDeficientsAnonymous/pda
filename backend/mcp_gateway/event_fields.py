import json
from datetime import datetime
from typing import Annotated, Any

from community._event_schemas import EventIn, EventPatchIn
from community._event_tags import list_event_tags
from community._validation import ValidationException
from community.models import EventType, PageVisibility, is_official_or_club
from config.validation_handlers import _serialize_pydantic_error, _serialize_validation_exception
from django.conf import settings
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import AfterValidator, BaseModel, Field, ValidationError, create_model
from users.models import User

from mcp_gateway.server import BASE_URL
from mcp_gateway.view_calls import call_view

_WHEN = "new york local time, e.g. 2026-11-07T11:00"


def _new_york(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    local = value.replace(tzinfo=settings.COMMUNITY_TZ)
    if value.tzinfo is not None and value.utcoffset() != local.utcoffset():
        offset = local.isoformat()[-6:]
        raise ValueError(
            f"new york is at {offset} on {value.date()}; send new york local time with no offset"
        )
    return local


NewYorkTime = Annotated[datetime | None, AfterValidator(_new_york)]


class EventFields(BaseModel):
    title: str = Field(description="event title")
    description: str = Field("", description="event description shown on the event page")
    start_datetime: NewYorkTime = Field(None, description=f"start, {_WHEN}")
    end_datetime: NewYorkTime = Field(None, description=f"end, {_WHEN}")
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


def _build[T: BaseModel](schema: type[T], data: dict[str, Any]) -> T:
    try:
        return schema(**data)
    except ValidationException as exc:
        detail = [_serialize_validation_exception(exc)]
        raise ToolError(json.dumps({"status": exc.status_code, "detail": detail})) from exc
    except ValidationError as exc:
        detail = [_serialize_pydantic_error({**err}) for err in exc.errors()]
        raise ToolError(json.dumps({"status": 422, "detail": detail})) from exc


async def to_event_in(fields: EventFields, user: User, **extra: Any) -> EventIn:
    data = fields.model_dump(mode="json", exclude={"tags"})
    tag_ids = list((await _tags(fields.tags, user)).values())
    return _build(EventIn, {**data, "tag_ids": tag_ids, **extra})


async def to_event_patch(
    changes: dict[str, Any], user: User, **extra: Any
) -> tuple[EventPatchIn, dict[str, Any]]:
    """return(tuple): the patch, and the changes with tags as their stored names."""
    data = {key: value for key, value in changes.items() if key != "tags"}
    if "tags" in changes:
        tags = await _tags(changes["tags"], user)
        data["tag_ids"] = list(tags.values())
        changes = {**changes, "tags": sorted(tags)}
    return _build(EventPatchIn, {**data, **extra}), changes


def _local(value: str | None) -> str | None:
    return value and datetime.fromisoformat(value).astimezone(settings.COMMUNITY_TZ).isoformat()


def event_summary(event: dict[str, Any]) -> dict[str, Any]:
    summary = {key: event[key] for key in EventFields.model_fields if key != "tags"}
    summary["start_datetime"] = _local(event["start_datetime"])
    summary["end_datetime"] = _local(event["end_datetime"])
    summary["tags"] = sorted(tag["name"] for tag in event["tags"])
    url = f"{BASE_URL}/events/{event['slug'] or event['id']}"
    return {"id": event["id"], "status": event["status"], "url": url, **summary}


def event_diff(event: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    before = event_summary(event)
    after = {
        key: _local(value) if key.endswith("_datetime") else value for key, value in changes.items()
    }
    return {
        key: {"before": before[key], "after": value}
        for key, value in after.items()
        if before[key] != value
    }


def update_notes(event: dict[str, Any], changes: dict[str, Any]) -> list[str]:
    notes = []
    new_type = changes.get("event_type", event["event_type"])
    plus_ones = changes.get("allow_plus_ones", event["allow_plus_ones"])
    if is_official_or_club(new_type) and plus_ones:
        if new_type != event["event_type"] or not event["allow_plus_ones"]:
            notes.append("plus-ones will be turned off: official and club events don't allow them")
    old_max, new_max = event["max_attendees"], changes.get("max_attendees")
    raised = new_max is not None and (old_max is None or new_max > old_max)
    if raised and event["waitlisted_count"]:
        notes.append("raising capacity moves waitlisted members to going and emails them")
    return notes
