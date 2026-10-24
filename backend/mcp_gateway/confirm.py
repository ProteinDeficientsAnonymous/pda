import hashlib
import json
from typing import Any, NamedTuple

from django.core import signing
from mcp.server.mcpserver.exceptions import ToolError

_SALT = "mcp_gateway.confirm"
MAX_AGE_SECONDS = 15 * 60


class Confirmed(NamedTuple):
    user_id: Any
    event_id: str
    action: str
    changes: Any
    state: Any


def _digest(bound: Confirmed) -> str:
    return hashlib.sha256(json.dumps(bound, sort_keys=True, default=str).encode()).hexdigest()


def issue_confirm_token(bound: Confirmed) -> str:
    return signing.dumps(_digest(bound), salt=_SALT)


def check_confirm_token(token: str, bound: Confirmed) -> None:
    try:
        signed = signing.loads(token, salt=_SALT, max_age=MAX_AGE_SECONDS)
    except signing.BadSignature:
        signed = None
    if signed != _digest(bound):
        raise ToolError(
            "confirm_token is expired or doesn't match this event, user and these exact changes. "
            "call again without confirm_token for a fresh preview, show it and ask the user again."
        )
