from datetime import timedelta
from typing import Annotated, Any

from asgiref.sync import sync_to_async
from django.utils import timezone
from pydantic import Field
from users._member_status import count_members_by_status
from users.permissions import PermissionKey

from mcp_gateway.server import pda_tool


@pda_tool(
    PermissionKey.MANAGE_USERS,
    description=(
        "count pda members by status. members only: people who just rsvp'd publicly aren't "
        "counted. total = every member. active, still_onboarding, paused and archived don't "
        "overlap and add up to total (except the rare member deactivated in the django admin): "
        "archived = account deleted, by an admin or by the member themselves; paused = paused by "
        "an admin, not archived; still_onboarding = not paused or archived but hasn't finished "
        "setting up their account yet; active = everyone else, set up and able to use the site. "
        "new_in_period = members whose membership started in the last period_days days, counted "
        "from the later of their latest join request approval and their account creation, "
        "whatever their status now, so it overlaps the other counts."
    ),
)
async def member_totals(
    period_days: Annotated[
        int, Field(ge=1, le=365, description="window for new_in_period, in days back from now")
    ] = 30,
) -> dict[str, Any]:
    since = timezone.now() - timedelta(days=period_days)
    totals = await sync_to_async(count_members_by_status)(since)
    return {**totals, "period_days": period_days, "period_start": since.isoformat()}
