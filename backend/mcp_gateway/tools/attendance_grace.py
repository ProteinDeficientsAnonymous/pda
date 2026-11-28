from datetime import date
from typing import Annotated, Any
from uuid import UUID

from community.attendance.clock import attendance_deadline
from community.attendance.report import AttendanceGraceIn, extend_attendance_grace
from django.utils import timezone
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from users.member_search import with_second_last_qualifying_at
from users.models import User
from users.permissions import PermissionKey

from mcp_gateway.confirm import Confirmed, ConfirmToken, issue_confirm_token, use_confirm_token
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.view_calls import call_view

MAX_BATCH = 50


def _summary(member: User) -> dict[str, str]:
    return {"id": str(member.pk), "name": member.full_name}


async def _members(member_ids: list[UUID]) -> dict[UUID, User]:
    found = {m.pk: m async for m in User.objects.members_or_archived().filter(pk__in=member_ids)}
    missing = [str(i) for i in member_ids if i not in found]
    if missing:
        raise ToolError(f"no member with id {', '.join(missing)}")
    return found


async def _deadlines(member_ids: list[UUID]) -> dict[UUID, date]:
    users = with_second_last_qualifying_at(User.objects.active_members().filter(pk__in=member_ids))
    deadlines = {}
    async for u in users:
        second_last = u.second_last_qualifying_at
        deadlines[u.pk] = attendance_deadline(
            u.date_joined.date(),
            second_last.date() if second_last else None,
            u.attendance_grace_until,
        )
    return deadlines


def _skip_reason(current: date | None, grace_until: date) -> str | None:
    if current is None:
        return "not an active member"
    if current >= grace_until:
        return f"deadline already {current}"
    return None


async def _plan(member_ids: list[UUID], grace_until: date) -> tuple[list[dict], list[dict]]:
    ids = list(dict.fromkeys(member_ids))
    members = await _members(ids)
    deadlines = await _deadlines(ids)
    batch, skipped = [], []
    for member_id in ids:
        summary = _summary(members[member_id])
        current = deadlines.get(member_id)
        reason = _skip_reason(current, grace_until)
        if reason:
            skipped.append({**summary, "reason": reason})
        else:
            batch.append({"member": summary, "deadline": str(current)})
    return batch, skipped


async def _extend(user: User, batch: list[dict], grace_until: date) -> tuple[list, list]:
    extended, failed = [], []
    for item in batch:
        try:
            await call_view(
                extend_attendance_grace,
                user,
                user_id=UUID(item["member"]["id"]),
                payload=AttendanceGraceIn(grace_until=grace_until),
            )
        except ToolError as exc:
            failed.append({**item["member"], "error": str(exc)})
            continue
        extended.append(item["member"])
    return extended, failed


@pda_tool(
    PermissionKey.MANAGE_USERS,
    description=(
        "push one or more members' 2-event deadline out to grace_until (up to "
        f"{MAX_BATCH} ids), like the attendance tab's extend grace button; the pause-side "
        "partner of set_attendance_pause. until then they aren't pause candidates and their "
        "attendance reminders don't come due. members whose deadline is already on or after "
        "grace_until, or who aren't active members, are listed under skipped. the first call "
        "changes nothing and returns each member's current deadline and one confirm_token: "
        "show it, get an explicit yes, then call again with the same arguments and the token."
    ),
)
async def extend_attendance_graces(
    member_ids: Annotated[
        list[UUID],
        Field(
            min_length=1, max_length=MAX_BATCH, description="the members' ids, from find_members"
        ),
    ],
    grace_until: Annotated[date, Field(description="the new deadline, after today")],
    confirm_token: ConfirmToken = None,
) -> dict[str, Any]:
    user = await current_user()
    if grace_until <= timezone.now().date():
        raise ToolError("grace_until must be after today")
    batch, skipped = await _plan(member_ids, grace_until)
    if not batch:
        raise ToolError("nobody listed would get a later deadline; nothing to do")
    bound = Confirmed(
        user.pk,
        target_id=",".join(sorted(b["member"]["id"] for b in batch)),
        action="extend_attendance_graces",
        changes=str(grace_until),
        state=batch,
    )
    result = {"new_deadline": str(grace_until), "skipped": skipped}
    if confirm_token is None:
        return {"to_extend": batch, **result, "confirm_token": issue_confirm_token(bound)}

    await use_confirm_token(confirm_token, bound)
    extended, failed = await _extend(user, batch, grace_until)
    return {"extended": extended, "failed": failed, **result}
