import json
from collections.abc import Callable
from io import BytesIO
from typing import Any

from asgiref.sync import sync_to_async
from community._validation import ValidationException
from config.audit import mark_request_via_mcp
from config.validation_handlers import _serialize_validation_exception
from django.core.handlers.asgi import ASGIRequest
from django.http import HttpRequest
from mcp.server.mcpserver.exceptions import ToolError
from ninja.responses import Status
from pydantic import BaseModel
from pydantic_core import to_jsonable_python
from users.models import User

from mcp_gateway.asgi_router import mcp_http_scope

# The bearer token and body framing belong to the MCP call, not the view call.
_DROPPED_META = frozenset({"HTTP_AUTHORIZATION", "HTTP_COOKIE", "CONTENT_LENGTH", "CONTENT_TYPE"})


def _view_request(user: User) -> HttpRequest:
    request = HttpRequest()
    scope = mcp_http_scope.get()
    if scope is not None:
        meta = ASGIRequest(scope, BytesIO()).META  # ty: ignore[too-many-positional-arguments]
        request.META = {key: value for key, value in meta.items() if key not in _DROPPED_META}
    request.method = "POST"
    request.path = request.path_info = "/mcp"
    request.auth = request.user = user  # ty: ignore[unresolved-attribute]
    mark_request_via_mcp(request)
    return request


def _jsonable(value: Any) -> Any:
    if isinstance(value, Status):
        return _jsonable(value.value)
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    return to_jsonable_python(value)


def _tool_error(status: int, detail: Any) -> ToolError:
    return ToolError(json.dumps({"status": status, "detail": detail}))


async def call_view(view: Callable[..., Any], user: User, *args: Any, **kwargs: Any) -> Any:
    """Run a ninja route handler as `user`; return its body as JSON-able data or raise ToolError."""
    request = _view_request(user)
    # No outer atomic, like the website: a rollback would undo the DB-backed rate-limit counter.
    try:
        result = await sync_to_async(view)(request, *args, **kwargs)
    except ValidationException as exc:
        raise _tool_error(exc.status_code, [_serialize_validation_exception(exc)]) from exc
    if isinstance(result, Status) and result.status_code >= 400:
        body = _jsonable(result.value)
        raise _tool_error(
            result.status_code, body.get("detail", body) if isinstance(body, dict) else body
        )
    return _jsonable(result)
