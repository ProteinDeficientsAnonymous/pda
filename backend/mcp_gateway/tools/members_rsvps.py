from datetime import timedelta
from typing import Annotated, Any
from uuid import UUID

from asgiref.sync import sync_to_async
from community.attendance.analytics import qualifying_attendance_q
from community.models import EventRSVP
from django.db.models import BooleanField, Case, F, When
from django.utils import timezone
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from pydantic_core import to_jsonable_python
from users.models import User
from users.permissions import PermissionKey

from mcp_gateway.server import pda_tool

_EVENT_FIELDS = ("title", "slug", "event_type", "status", "start_datetime")
_RSVP_FIELDS = (
    *("status", "attendance", "checked_in_at", "has_plus_one", "plus_one_attendance"),
    *("cancelled_at", "created_at", "status_changed_at"),
)


def _row(rsvp: EventRSVP) -> dict[str, Any]:
    event = {f"event_{f}": getattr(rsvp.event, f) for f in _EVENT_FIELDS}
    values = {f: getattr(rsvp, f) for f in _RSVP_FIELDS}
    return to_jsonable_python(
        {"event_id": str(rsvp.event_id), **event, **values, "qualifying": rsvp.qualifying}
    )


def member_rsvps_page(
    member_id: UUID, since_days: int | None, limit: int, offset: int
) -> dict[str, Any]:
    member = User.objects.members().filter(pk=member_id).only("first_name", "last_name").first()
    if member is None:
        raise ToolError("no member with that id")
    qs = EventRSVP.objects.filter(user=member)
    if since_days is not None:
        qs = qs.filter(event__start_datetime__gte=timezone.now() - timedelta(days=since_days))
    total = qs.count()
    rows = (
        qs.select_related("event")
        .annotate(
            qualifying=Case(
                When(qualifying_attendance_q(), then=True),
                default=False,
                output_field=BooleanField(),
            )
        )
        .order_by(F("event__start_datetime").desc(nulls_last=True), "id")
    )
    return {
        "member": {"id": str(member.id), "name": member.full_name},
        "rsvps": [_row(r) for r in rows[offset : offset + limit]],
        "total": total,
        "next_offset": offset + limit if offset + limit < total else None,
    }


@pda_tool(
    PermissionKey.MANAGE_USERS,
    description=(
        "list one member's rsvps, latest event first, with the attendance a host marked "
        "(unknown until marked). get the id from find_members by name. every rsvp is listed, "
        "including cancelled, draft and deleted events. qualifying = counts toward qualifying "
        "attendance in find_members and the analytics screen. paged: fetch more with "
        "offset=next_offset, keeping the same member and since_days."
    ),
)
async def member_rsvps(
    member: Annotated[UUID, Field(description="member id from find_members")],
    since_days: Annotated[
        int | None,
        Field(
            ge=1,
            le=3650,
            description="only events starting in the last n days or later "
            "(future events included); undated events are left out",
        ),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=100, description="rsvps per page")] = 50,
    offset: Annotated[
        int, Field(ge=0, le=100_000, description="next_offset from the previous page")
    ] = 0,
) -> dict[str, Any]:
    return await sync_to_async(member_rsvps_page)(member, since_days, limit, offset)
