import json
from datetime import datetime
from typing import Any

from community._event_schemas import EventIn
from community._event_tags import list_event_tags
from community._validation import ValidationException
from community.models import EventType, PageVisibility
from config.validation_handlers import _serialize_validation_exception
from django.conf import settings
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import AwareDatetime, BaseModel, Field, ValidationError
from users.models import User

from mcp_gateway.server import BASE_URL
from mcp_gateway.view_calls import call_view

_WHEN = "iso 8601 with utc offset. pda events are in new york time, e.g. 2026-11-07T11:00:00-05:00"


class EventFields(BaseModel):
    title: str = Field(description="event title")
    description: str = Field("", description="event description shown on the event page")
    start_datetime: AwareDatetime | None = Field(None, description=f"start, {_WHEN}")
    end_datetime: AwareDatetime | None = Field(None, description=f"end, {_WHEN}")
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


async def _tag_ids(names: list[str], user: User) -> list[str]:
    by_name = {tag["name"].lower(): tag["id"] for tag in await call_view(list_event_tags, user)}
    unknown = [name for name in names if name.strip().lower() not in by_name]
    if unknown:
        valid = ", ".join(sorted(by_name)) or "none"
        raise ToolError(f"unknown tags: {', '.join(unknown)}. valid tags: {valid}")
    return [by_name[name.strip().lower()] for name in names]


async def to_event_in(fields: EventFields, user: User, **extra: Any) -> EventIn:
    data = fields.model_dump(mode="json", exclude={"tags"})
    try:
        return EventIn(**data, tag_ids=await _tag_ids(fields.tags, user), **extra)
    except ValidationException as exc:
        raise ToolError(json.dumps(_serialize_validation_exception(exc))) from exc
    except ValidationError as exc:
        raise ToolError(str(exc)) from exc


def _local(value: str | None) -> str | None:
    return value and datetime.fromisoformat(value).astimezone(settings.COMMUNITY_TZ).isoformat()


def event_summary(event: dict[str, Any]) -> dict[str, Any]:
    summary = {key: event[key] for key in EventFields.model_fields if key != "tags"}
    summary["start_datetime"] = _local(event["start_datetime"])
    summary["end_datetime"] = _local(event["end_datetime"])
    summary["tags"] = [tag["name"] for tag in event["tags"]]
    url = f"{BASE_URL}/events/{event['slug'] or event['id']}"
    return {"id": event["id"], "status": event["status"], "url": url, **summary}
