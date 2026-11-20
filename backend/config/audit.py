"""Audit logging helper for structured security and admin action logging."""

import ipaddress
import logging
from types import SimpleNamespace
from typing import TYPE_CHECKING, NamedTuple

from audit.models import AuditLogEntry, AuditTargetType
from django.db import transaction

from config.ratelimit import client_ip

if TYPE_CHECKING:
    from community.validation import InvalidStateTransition

__all__ = [
    "AuditTarget",
    "AuditTargetType",
    "actor_request",
    "audit_log",
    "audit_log_before_raise",
    "audit_rejected_transition",
    "flush_rollback_safe_audits",
    "is_request_anonymized",
    "is_request_via_mcp",
    "mark_request_anonymized",
    "mark_request_via_mcp",
]

_ANONYMIZED_ATTR = "pda_anonymized"
_VIA_MCP_ATTR = "pda_via_mcp"
_HELD_AUDITS_ATTR = "pda_held_audits"


def mark_request_anonymized(request) -> None:
    """Drop the actor from this request's audit rows and request log line."""
    setattr(request, _ANONYMIZED_ATTR, True)


def is_request_anonymized(request) -> bool:
    return getattr(request, _ANONYMIZED_ATTR, False)


def mark_request_via_mcp(request) -> None:
    setattr(request, _VIA_MCP_ATTR, True)


def is_request_via_mcp(request) -> bool:
    return getattr(request, _VIA_MCP_ATTR, False)


class AuditTarget(NamedTuple):
    """The audited object and what happened to it: type, id, and context details."""

    type: AuditTargetType | str = ""
    id: str = ""
    details: dict | None = None


_audit_logger = logging.getLogger("pda.audit")


def _valid_ip(value: str) -> str | None:
    # client_ip can return 'anon' or an unvalidated XFF hop; Postgres rejects both.
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def _persist(**fields) -> None:
    try:
        AuditLogEntry.objects.create(**fields)
    except Exception:
        _audit_logger.exception("audit_persist_failed", extra={"action": fields.get("action")})


def actor_request(request, actor=None):
    """Return request when given, else a minimal auth carrier for non-HTTP callers."""
    return request if request is not None or actor is None else SimpleNamespace(auth=actor)


def _actor_and_ip(request):
    # "anon" fails _valid_ip, so an anonymized or request-less entry persists no IP.
    if request is None or is_request_anonymized(request):
        return None, "anon"
    user = getattr(request, "auth", None)
    actor = user if user and hasattr(user, "pk") else None
    # Spoof-resistant client IP (rightmost non-internal hop); see config/ratelimit.py.
    ip = client_ip(request) if hasattr(request, "META") else "anon"
    return actor, ip


def _emit(level: int, action: str, request, target: AuditTarget | None) -> dict:
    """Log the entry and return the audit row's fields."""
    target_type, target_id, details = target or AuditTarget()
    details = {**(details or {}), "via": "mcp"} if is_request_via_mcp(request) else details or {}
    user, ip_address = _actor_and_ip(request)
    if user:
        actor_id = str(user.pk)
        actor_name = getattr(user, "full_name", None) or str(user)
    else:
        actor_id = "anonymous"
        actor_name = "anonymous"

    _audit_logger.log(
        level,
        "%s by %s",
        action,
        actor_name,
        extra={
            "audit": True,
            "action": action,
            "actor_id": actor_id,
            "actor_name": actor_name,
            "target_type": target_type,
            "target_id": target_id,
            "details": details,
            "ip_address": ip_address,
        },
    )
    return {
        "action": action,
        "actor": user,
        "actor_label": actor_name,
        "target_type": target_type,
        "target_id": target_id,
        "details": details,
        "ip_address": _valid_ip(ip_address),
        "level": level,
    }


def audit_log(
    level: int,
    action: str,
    request,
    target: AuditTarget | None = None,
    *,
    persist: bool = True,
) -> None:
    """Emit a structured audit log entry.

    Args:
        level: logging.INFO or logging.WARNING
        action: verb describing the event (e.g. 'login_success', 'user_deleted')
        request: the Django/Ninja HttpRequest (used for actor and IP)
        target: AuditTarget(type, id, details) for the affected object
        persist: write a row to the audit table; False for console-only noise
    """
    fields = _emit(level, action, request, target)
    if persist:
        # on_commit so a rolled-back action leaves no row — the action didn't happen.
        transaction.on_commit(lambda: _persist(**fields))


def audit_log_before_raise(
    level: int, action: str, request, target: AuditTarget | None = None
) -> None:
    """Audit a refused request right before raising; the row outlives the rollback the raise causes."""
    fields = _emit(level, action, request, target)
    if not transaction.get_connection().in_atomic_block:
        _persist(**fields)
        return
    held = getattr(request, _HELD_AUDITS_ATTR, [])
    setattr(request, _HELD_AUDITS_ATTR, [*held, fields])


def flush_rollback_safe_audits(request) -> None:
    """Write rows held by audit_log_before_raise; RequestLoggingMiddleware and MCP call_view call this."""
    for fields in getattr(request, _HELD_AUDITS_ATTR, []):
        _persist(**fields)
    setattr(request, _HELD_AUDITS_ATTR, [])


def audit_rejected_transition(request, exc: "InvalidStateTransition", *, actor=None) -> None:
    """Persist a rejected state transition so it survives the enclosing atomic rollback."""
    if exc.audited:
        return
    exc.audited = True
    audit_log_before_raise(
        logging.WARNING,
        exc.failure.action,
        actor_request(request, actor),
        target=AuditTarget(
            type=exc.failure.target_type,
            id=exc.failure.target_id,
            details=exc.failure.details(exc.code),
        ),
    )
