from typing import Annotated, Any
from uuid import UUID

from community.clubs.api import ClubIn
from community.clubs.api import create_club as create_view
from community.clubs.api import delete_club as delete_view
from community.clubs.api import list_clubs as list_view
from community.clubs.api import update_club as update_view
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
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
