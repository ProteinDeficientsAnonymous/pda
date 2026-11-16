from datetime import date
from typing import Annotated, Any
from uuid import UUID

from community.models import ReserveEntryKind
from community.reserve.manage import create_reserve_entry as create_view
from community.reserve.manage import delete_reserve_entry as delete_view
from community.reserve.manage import update_reserve_entry as update_view
from community.reserve.read import get_reserve as get_view
from community.reserve.schemas import Money, ReserveEntryIn, ReserveEntryPatchIn
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from mcp_gateway.confirm import Confirmed, ConfirmToken, issue_confirm_token, use_confirm_token
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.view_calls import call_view

EntryId = Annotated[UUID, Field(description="the entry's id, from list_reserve_entries")]
Amount = Annotated[Money | None, Field(description="dollars, e.g. 103.65")]


class ReserveEntryFields(BaseModel):
    label: Annotated[str | None, Field(description="e.g. '9/12 hudson river walk + peacefood'")] = (
        None
    )
    kind: Annotated[
        ReserveEntryKind | None,
        Field(description="event (default), cost or donation; the table lists them in that order"),
    ] = None
    occurred_on: Annotated[date | None, Field(description="event or payment date")] = None
    collected: Amount = None
    paid_out: Amount = None
    facilitator_drinks: Amount = None


@pda_tool(
    PermissionKey.EDIT_GUIDELINES,
    description=(
        "list the reserve breakdown shown on the donate page: one entry per event, donation or "
        "cost, with collected, paid_out, facilitator_drinks and the computed left_over"
    ),
)
async def list_reserve_entries() -> dict[str, Any]:
    return await call_view(get_view, await current_user())


@pda_tool(
    PermissionKey.EDIT_GUIDELINES,
    description=(
        "add or update a line on the donate page's public reserve breakdown. without entry_id it "
        "adds a new entry (label and occurred_on required); with entry_id it changes only the "
        "fields given. amounts are non-negative dollars: money members paid in goes in "
        "collected, restaurant bills, refunds and reimbursed costs go in paid_out. this is "
        "public, so never put member names in the label. show the user the values and get "
        "their ok before calling."
    ),
)
async def save_reserve_entry(
    fields: ReserveEntryFields,
    entry_id: Annotated[UUID | None, Field(description="omit to add a new entry")] = None,
) -> dict[str, Any]:
    user = await current_user()
    given = fields.model_dump(exclude_none=True)
    if entry_id is not None:
        return await call_view(
            update_view, user, entry_id=entry_id, payload=ReserveEntryPatchIn(**given)
        )
    if fields.label is None or fields.occurred_on is None:
        raise ToolError("a new entry needs a label and occurred_on")
    return await call_view(create_view, user, payload=ReserveEntryIn(**given))


@pda_tool(
    PermissionKey.EDIT_GUIDELINES,
    description=(
        "remove a line from the donate page's reserve breakdown. the first call changes nothing "
        "and returns the entry and a confirm_token: show it, get an explicit yes, then call "
        "again with the same entry_id and the token."
    ),
)
async def delete_reserve_entry(
    entry_id: EntryId, confirm_token: ConfirmToken = None
) -> dict[str, Any]:
    user = await current_user()
    reserve = await call_view(get_view, user)
    entry = next((e for e in reserve["entries"] if e["id"] == str(entry_id)), None)
    if entry is None:
        raise ToolError(f"no reserve entry with id {entry_id}")
    bound = Confirmed(
        user.pk, target_id=str(entry_id), action="delete_reserve_entry", changes=None, state=entry
    )
    if confirm_token is None:
        return {"entry": entry, "confirm_token": issue_confirm_token(bound)}

    await use_confirm_token(confirm_token, bound)
    await call_view(delete_view, user, entry_id=entry_id)
    return {"deleted": entry}
