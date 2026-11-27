from typing import Annotated, Any

from notifications.member_blasts.api import BlastIn, preview_blast, send_blast, send_test
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field, ValidationError
from users.permissions import PermissionKey

from mcp_gateway.confirm import Confirmed, ConfirmToken, issue_confirm_token, use_confirm_token
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.view_calls import call_view


@pda_tool(
    PermissionKey.SEND_EMAIL_BLAST,
    description=(
        "email every member at once. the first call sends nothing: it returns the recipient "
        "count, the email as it will look, and a confirm_token. show the preview, get an "
        "explicit yes, then call again with the same subject, body_html and the token. "
        "send_test_to_me sends it only to you first. if the result status is unknown, or "
        "failed with sent_count above 0, some emails may have gone out: tell the user to "
        "check brevo and don't send again."
    ),
)
async def send_member_email_blast(
    subject: Annotated[str, Field(min_length=1, max_length=150)],
    body_html: Annotated[str, Field(min_length=1, max_length=100_000)],
    send_test_to_me: bool = False,
    confirm_token: ConfirmToken = None,
) -> dict[str, Any]:
    user = await current_user()
    try:
        payload = BlastIn(subject=subject, body_html=body_html)
    except ValidationError as exc:
        field = str(exc.errors()[0]["loc"][0])
        limit = "150" if field == "subject" else "100000"
        raise ToolError(f"{field} must be 1-{limit} characters") from exc
    if send_test_to_me:
        result = await call_view(send_test, user, payload=payload)
        return {"test_sent_to": "you", "sent": result["sent"]}
    preview = await call_view(preview_blast, user, payload=payload)
    bound = Confirmed(user.pk, "member_blast", "send", [subject, preview["html"]], None)
    if confirm_token is None:
        return {**preview, "confirm_token": issue_confirm_token(bound)}
    await use_confirm_token(confirm_token, bound)
    return await call_view(send_blast, user, payload=payload)
