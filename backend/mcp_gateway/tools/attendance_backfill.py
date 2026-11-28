from datetime import date
from typing import Annotated, Any
from uuid import UUID

from asgiref.sync import sync_to_async
from community.attendance.mark import mark_attendance
from community.attendance.mark_schemas import AttendanceMarkIn
from community.field_limits import FieldLimit
from community.models import Event, EventRSVP, EventType
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field
from users.helpers import visible_display_name
from users.models import User
from users.permissions import PermissionKey

from mcp_gateway.confirm import Confirmed, ConfirmToken, issue_confirm_token, use_confirm_token
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.view_calls import call_view


class NewLegacyEvent(BaseModel):
    title: str = Field(min_length=1, max_length=FieldLimit.TITLE)
    event_date: date
    event_type: EventType = Field(EventType.COMMUNITY, description="community, official or club")


def _event(event_id: UUID | None, new: NewLegacyEvent | None) -> dict[str, Any]:
    if (event_id is None) == (new is None):
        raise ToolError("give exactly one of event_id or new_legacy_event")
    if new is not None:
        return {"id": None, **new.model_dump(mode="json"), "new_legacy_event": True}
    event = Event.objects.filter(pk=event_id).first()
    if event is None:
        raise ToolError(f"no event with id {event_id}")
    when = event.start_datetime.date().isoformat() if event.start_datetime else None
    return {"id": str(event.pk), "title": event.title, "date": when, "status": event.status}


def _preview(viewer: User, event: dict[str, Any], member_ids: list[UUID]) -> dict[str, Any]:
    users = {u.pk: u for u in User.objects.filter(pk__in=member_ids)}
    rsvps = {}
    if event["id"]:
        rsvps = {
            r.user_id: r
            for r in EventRSVP.objects.filter(event_id=event["id"], user_id__in=member_ids)
        }
    members = [
        {
            "id": str(pk),
            "name": visible_display_name(users[pk], viewer),
            "current_rsvp": rsvps[pk].status if pk in rsvps else None,
            "current_attendance": rsvps[pk].attendance if pk in rsvps else None,
        }
        for pk in member_ids
        if pk in users
    ]
    unknown = [str(pk) for pk in member_ids if pk not in users]
    return {"event": event, "members": members, "unknown_ids": unknown}


def _build_preview(
    viewer: User, event_id: UUID | None, new: NewLegacyEvent | None, ids: list[UUID]
) -> dict[str, Any]:
    return _preview(viewer, _event(event_id, new), ids)


@pda_tool(
    PermissionKey.MANAGE_USERS,
    description=(
        "mark members as attended at an event whether or not they rsvped, like the website's "
        "mark attendance page; for backfilling attendance history, past events included. give "
        "event_id for an existing event, or new_legacy_event to create a members-only legacy "
        "event kept off the calendar. each member gets a going rsvp marked attended, replacing "
        "any rsvp they had; nobody is emailed. the first call changes nothing and returns the "
        "event, each member's current rsvp and a confirm_token: show that, get an explicit yes, "
        "then call again with the same arguments and the token."
    ),
)
async def mark_attended(
    member_ids: Annotated[
        list[UUID], Field(min_length=1, description="member ids, from find_members")
    ],
    event_id: Annotated[UUID | None, Field(description="an existing event's id")] = None,
    new_legacy_event: NewLegacyEvent | None = None,
    confirm_token: ConfirmToken = None,
) -> dict[str, Any]:
    user = await current_user()
    ids = list(dict.fromkeys(member_ids))
    preview = await sync_to_async(_build_preview)(user, event_id, new_legacy_event, ids)
    new = new_legacy_event
    payload = AttendanceMarkIn(
        event_id=str(event_id) if event_id else None,
        event_title=new.title if new else None,
        event_date=new.event_date if new else None,
        event_type=new.event_type if new else None,
        user_ids=[str(pk) for pk in ids],
    )
    bound = Confirmed(
        user.pk,
        target_id=str(event_id) if event_id else "new_legacy_event",
        action="mark_attended",
        changes=payload.model_dump(mode="json"),
        state=preview,
    )
    if confirm_token is None:
        return {**preview, "confirm_token": issue_confirm_token(bound)}

    await use_confirm_token(confirm_token, bound)
    return await call_view(mark_attendance, user, payload)
