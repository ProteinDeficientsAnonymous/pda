import hashlib
import json
import secrets
from typing import Any, NamedTuple

from django.core import signing
from django.core.cache import caches
from mcp.server.mcpserver.exceptions import ToolError

_SALT = "mcp_gateway.confirm"
MAX_AGE_SECONDS = 15 * 60


class Confirmed(NamedTuple):
    user_id: Any
    target_id: str
    action: str
    changes: Any
    state: Any


def _digest(bound: Confirmed) -> str:
    return hashlib.sha256(json.dumps(bound, sort_keys=True, default=str).encode()).hexdigest()


def issue_confirm_token(bound: Confirmed) -> str:
    nonce = secrets.token_urlsafe(16)
    return signing.dumps({"digest": _digest(bound), "nonce": nonce}, salt=_SALT)


_AGAIN = "call again without confirm_token for a fresh preview, show it and ask the user again."


async def use_confirm_token(token: str, bound: Confirmed) -> None:
    try:
        signed = signing.loads(token, salt=_SALT, max_age=MAX_AGE_SECONDS)
    except signing.BadSignature:
        signed = None
    if not isinstance(signed, dict) or signed.get("digest") != _digest(bound):
        raise ToolError(
            "confirm_token is expired or doesn't match this item, user and these exact changes. "
            + _AGAIN
        )
    # DB-backed cache so a token is single-use across workers.
    if not await caches["ratelimit"].aadd(f"mcp-confirm:{signed['nonce']}", 1, MAX_AGE_SECONDS):
        raise ToolError("confirm_token was already used. " + _AGAIN)
