from typing import Annotated, Any

from pydantic import Field
from users.permissions import PermissionKey

from mcp_gateway.cashapp_review import load_review, remember_csv, review_out
from mcp_gateway.server import current_user, pda_tool

MAX_CSV_CHARS = 2_000_000

EventRef = Annotated[str, Field(description="event id (uuid) or slug, e.g. from list_my_events")]
CsvText = Annotated[
    str,
    Field(
        min_length=1,
        max_length=MAX_CSV_CHARS,
        description="the cash app csv export's full contents, unedited",
    ),
]


@pda_tool(
    PermissionKey.IMPORT_PAYMENTS,
    description=(
        "check a cash app csv export against one event's rsvps. no payments are marked; the csv "
        "is kept on the server for an hour so verify_cashapp_payments can reuse it. pass the csv "
        "contents exactly as exported. lead with gap_list: guests who said they paid, or "
        "are attending a paid event, with no matching payment, so a host can follow up or verify "
        "them by hand. then show the confident matches, the unsure ones with their reason and "
        "candidates, and unplaced_payments, plus any amount_mismatch_leads and unreadable_rows. "
        "unplaced_payments, amount_mismatch_leads and unreadable_rows can't be applied here: a "
        "host verifies those guests by hand in the app. ask the user which confident or unsure "
        "matches to apply (unsure ones only when they pick the guest), then call "
        "verify_cashapp_payments with the review_id (valid for an hour). never verify anyone the "
        "user didn't confirm."
    ),
)
async def review_cashapp_payments(event: EventRef, csv_text: CsvText) -> dict[str, Any]:
    user = await current_user()
    loaded = await load_review(user, event, csv_text)
    await remember_csv(user, loaded, csv_text)
    return review_out(loaded)
