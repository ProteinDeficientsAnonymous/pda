from typing import Any

from notifications.member_blasts.api import BlastIn, preview_blast, send_blast, send_test
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
        "send_test_to_me sends it only to you first."
    ),
)
async def send_member_email_blast(
    subject: str,
    body_html: str,
    send_test_to_me: bool = False,
    confirm_token: ConfirmToken = None,
) -> dict[str, Any]:
    user = await current_user()
    payload = BlastIn(subject=subject, body_html=body_html)
    if send_test_to_me:
        await call_view(send_test, user, payload=payload)
        return {"test_sent_to": "you"}
    preview = await call_view(preview_blast, user, payload=payload)
    bound = Confirmed(user.pk, "member_blast", "send", [subject, preview["html"]], None)
    if confirm_token is None:
        return {**preview, "confirm_token": issue_confirm_token(bound)}
    await use_confirm_token(confirm_token, bound)
    return await call_view(send_blast, user, payload=payload)
