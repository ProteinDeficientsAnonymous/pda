from typing import Annotated, Any
from uuid import UUID

from asgiref.sync import sync_to_async
from community.clubs.api import ClubIn, ClubRepsIn
from community.clubs.api import create_club as create_view
from community.clubs.api import delete_club as delete_view
from community.clubs.api import list_club_reps as list_reps_view
from community.clubs.api import list_clubs as list_view
from community.clubs.api import set_club_reps as set_reps_view
from community.clubs.api import update_club as update_view
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from users.helpers import visible_name
from users.models import User
from users.permissions import PermissionKey

from mcp_gateway.confirm import Confirmed, ConfirmToken, issue_confirm_token, use_confirm_token
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.view_calls import call_view

ClubId = Annotated[UUID, Field(description="the club's id, from list_clubs")]


async def _club(user: User, club_id: UUID) -> dict[str, Any]:
    club = next((c for c in await call_view(list_view, user) if c["id"] == str(club_id)), None)
    if club is None:
        raise ToolError(f"no club with id {club_id}")
    return club


@pda_tool(
    description=(
        "list pda clubs (id, name, requirements to join). every club event belongs to one, and "
        "the join form asks applicants which ones they're interested in"
    )
)
async def list_clubs() -> list[dict[str, Any]]:
    return await call_view(list_view, await current_user())


@pda_tool(
    PermissionKey.MANAGE_EVENTS,
    description=(
        "add a club or change one. without club_id it adds a club (name required); with club_id "
        "it changes only the fields given. requirements is who can join, shown on the join form "
        "next to the name, e.g. 'must be dog parent // guardian'; an empty string clears it. the "
        "join form's clubs question updates on its own. show the user the values and get their "
        "ok before calling."
    ),
)
async def save_club(
    name: Annotated[str | None, Field(description="e.g. 'book club'")] = None,
    requirements: Annotated[str | None, Field(description="who can join; optional")] = None,
    club_id: Annotated[UUID | None, Field(description="omit to add a new club")] = None,
) -> dict[str, Any]:
    user = await current_user()
    if club_id is None:
        if not name:
            raise ToolError("a new club needs a name")
        payload = ClubIn(name=name, requirements=requirements or "")
        return await call_view(create_view, user, payload=payload)
    current = await _club(user, club_id)
    payload = ClubIn(
        name=current["name"] if name is None else name,
        requirements=current["requirements"] if requirements is None else requirements,
    )
    return await call_view(update_view, user, club_id=club_id, payload=payload)


@pda_tool(
    PermissionKey.MANAGE_EVENTS,
    description=(
        "delete a club. its events keep their details but lose their club, and it drops off the "
        "join form. the first call changes nothing and returns the club and a confirm_token: "
        "show it, get an explicit yes, then call again with the same club_id and the token."
    ),
)
async def delete_club(club_id: ClubId, confirm_token: ConfirmToken = None) -> dict[str, Any]:
    user = await current_user()
    club = await _club(user, club_id)
    bound = Confirmed(
        user.pk, target_id=str(club_id), action="delete_club", changes=None, state=club
    )
    if confirm_token is None:
        return {"club": club, "confirm_token": issue_confirm_token(bound)}

    await use_confirm_token(confirm_token, bound)
    await call_view(delete_view, user, club_id=club_id)
    return {"deleted": club}


@pda_tool(
    PermissionKey.MANAGE_EVENTS,
    description=(
        "list each pda club's reps (the members who get its monthly event reminders and can "
        "post its events). member ids work with set_club_reps."
    ),
)
async def list_club_reps() -> list[dict[str, Any]]:
    user = await current_user()
    names = {c["id"]: c["name"] for c in await call_view(list_view, user)}
    reps = await call_view(list_reps_view, user)
    return [{**item, "club_name": names.get(item["club_id"], "")} for item in reps]


def _named_reps(reps: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{"id": r["id"], "name": r["full_name"]} for r in reps]


@pda_tool(
    PermissionKey.MANAGE_EVENTS,
    description=(
        "add and/or remove reps on one club, leaving its other reps as they are. member ids "
        "come from find_members; only members can be reps. reps get the club's monthly event "
        "reminder emails and can post its events. the first call changes nothing and returns "
        "the club, its current reps, the resulting reps and a confirm_token: show that, get an "
        "explicit yes, then call again with the same arguments and the token."
    ),
)
async def set_club_reps(
    club_id: ClubId,
    add_member_ids: Annotated[list[UUID] | None, Field(description="member ids to add")] = None,
    remove_member_ids: Annotated[
        list[UUID] | None, Field(description="member ids to remove")
    ] = None,
    confirm_token: ConfirmToken = None,
) -> dict[str, Any]:
    user = await current_user()
    club = await _club(user, club_id)
    add_ids, remove_ids = add_member_ids or [], remove_member_ids or []
    if not (add_ids or remove_ids):
        raise ToolError("give add_member_ids and/or remove_member_ids")
    if set(add_ids) & set(remove_ids):
        raise ToolError("a member can't be both added and removed")

    added = {u.pk: u async for u in User.objects.members().filter(pk__in=add_ids)}
    not_members = sorted(str(i) for i in set(add_ids) - added.keys())
    if not_members:
        raise ToolError(f"not members: {', '.join(not_members)}; use find_members")

    entry = next(
        (r for r in await call_view(list_reps_view, user) if r["club_id"] == str(club_id)),
        {"reps": []},
    )
    current = _named_reps(entry["reps"])
    new = [r for r in current if UUID(r["id"]) not in remove_ids]
    known = {r["id"] for r in new}
    for member in added.values():
        if str(member.pk) not in known:
            name = (await sync_to_async(visible_name)(member, user))[1]
            new.append({"id": str(member.pk), "name": name})
    current_ids, new_ids = {r["id"] for r in current}, {r["id"] for r in new}
    if new_ids == current_ids:
        raise ToolError(f"{club['name']} already has exactly those reps; nothing to do")

    summary = {"id": club["id"], "name": club["name"]}
    bound = Confirmed(
        user.pk,
        target_id=str(club_id),
        action="set_club_reps",
        changes=sorted(new_ids),
        state=sorted(current_ids),
    )
    if confirm_token is None:
        return {
            "club": summary,
            "current_reps": current,
            "resulting_reps": new,
            "confirm_token": issue_confirm_token(bound),
        }

    await use_confirm_token(confirm_token, bound)
    result = await call_view(
        set_reps_view,
        user,
        club_id=club_id,
        payload=ClubRepsIn(user_ids=[UUID(i) for i in new_ids]),
    )
    return {"club": summary, "reps": _named_reps(result["reps"])}
