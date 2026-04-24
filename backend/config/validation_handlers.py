"""Global Ninja exception handlers that reshape validation errors to
``{ detail: [{code, field, params?}, ...] }`` so the frontend owns UI copy.

Two cases:
  1. ``ValidationException`` raised by our own validators — direct pass-through.
  2. ``ninja.errors.ValidationError`` — Ninja's wrapper around Pydantic
     errors during request parsing. Covers missing fields, type mismatches,
     and nested validator failures. If a validator raised a
     ``ValidationException``, pull its code out of ``ctx.error``.
"""

from typing import Any

from community._validation import ValidationException
from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import ValidationError as NinjaValidationError

_GENERIC_FIELD_INVALID = "field_invalid"
_GENERIC_FIELD_REQUIRED = "field_required"


def register_validation_handlers(api: NinjaAPI) -> None:
    @api.exception_handler(ValidationException)
    def _handle_validation_exception(
        request: HttpRequest, exc: ValidationException
    ) -> HttpResponse:
        response = api.create_response(
            request,
            {"detail": [_serialize_validation_exception(exc)]},
            status=exc.status_code,
        )
        if exc.clear_refresh_cookie:
            # Lazy import to keep users/ out of config/ dependency graph for
            # modules that don't need cookie-clearing.
            from users._refresh_cookie import clear_refresh_cookie

            clear_refresh_cookie(response)
        return response

    @api.exception_handler(NinjaValidationError)
    def _handle_ninja_validation_error(
        request: HttpRequest, exc: NinjaValidationError
    ) -> HttpResponse:
        return api.create_response(
            request,
            {"detail": [_serialize_pydantic_error(e) for e in exc.errors]},
            status=422,
        )


def _serialize_validation_exception(exc: ValidationException) -> dict[str, Any]:
    out: dict[str, Any] = {"code": exc.code, "field": exc.field}
    if exc.params:
        out["params"] = exc.params
    return out


def _serialize_pydantic_error(err: dict[str, Any]) -> dict[str, Any]:
    # When a validator raised a ValidationException, Pydantic's message takes
    # the form "Value error, <str(exc)>". Since str(ValidationException) is the
    # bare code (see __init__), we can recover it by stripping the prefix.
    # (Ninja stringifies ctx.error at the main.py level so we can't grab the
    # exception instance directly.)
    msg = err.get("msg", "") or ""
    if msg.startswith("Value error, "):
        code_candidate = msg.removeprefix("Value error, ").strip()
        if _looks_like_validation_code(code_candidate):
            return {"code": code_candidate, "field": _loc_to_field(err)}

    # Default Pydantic errors (type mismatches, missing, etc.) — map the most
    # common types to generic codes. The frontend falls back to a generic
    # message for anything it doesn't recognize.
    err_type = err.get("type", "")
    code = _GENERIC_FIELD_REQUIRED if err_type == "missing" else _GENERIC_FIELD_INVALID
    return {"code": code, "field": _loc_to_field(err)}


def _looks_like_validation_code(s: str) -> bool:
    # Stable codes are dotted snake_case identifiers (``event.foo_bar``,
    # ``role.not_found``). Guards against matching arbitrary free-text
    # ValueErrors that slip through uncaptured.
    if not s or not s.islower():
        return False
    return all(part.replace("_", "").isalnum() and part for part in s.split("."))


_NINJA_SOURCE_NAMES = frozenset({"body", "query", "path", "header", "form", "cookie", "file"})


def _loc_to_field(err: dict[str, Any]) -> str | None:
    # Ninja's loc looks like ("body", "<param-name>", "<field>", ...). Strip
    # the source prefix if present, then strip the handler's param name (one
    # element). What's left is the user-visible field path.
    loc = list(err.get("loc") or ())
    if loc and str(loc[0]) in _NINJA_SOURCE_NAMES:
        loc.pop(0)
    if loc:
        loc.pop(0)  # drop the handler's param variable name
    return ".".join(str(p) for p in loc) if loc else None
