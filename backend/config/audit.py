"""Audit logging helper for structured security and admin action logging."""

import ipaddress
import logging

from audit.models import AuditLogEntry, AuditTargetType
from django.db import transaction

from config.ratelimit import client_ip

__all__ = ["AuditTargetType", "audit_log"]

_audit_logger = logging.getLogger("pda.audit")


def _valid_ip(value: str) -> str | None:
    # client_ip can return 'anon' or an unvalidated XFF hop; Postgres rejects
    # either, and _persist would swallow that as a silently lost audit row.
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def _persist(**fields) -> None:
    # An audit write must never turn a successful user action into a 500.
    try:
        AuditLogEntry.objects.create(**fields)
    except Exception:
        _audit_logger.exception("audit_persist_failed", extra={"action": fields.get("action")})


def audit_log(  # noqa: PLR0913
    level: int,
    action: str,
    request,
    target_type: AuditTargetType | str = "",
    target_id: str = "",
    details: dict | None = None,
    *,
    persist: bool = True,
) -> None:
    """Emit a structured audit log entry.

    Args:
        level: logging.INFO or logging.WARNING
        action: verb describing the event (e.g. 'login_success', 'user_deleted')
        request: the Django/Ninja HttpRequest (used for actor and IP)
        target_type: AuditTargetType member for the affected object
        target_id: string ID of the affected object
        details: optional context dict (avoid including raw phone numbers or tokens)
        persist: write a row to the audit table; pass False for access-control
            noise and bot traffic, which belong in the console log only
    """
    user = getattr(request, "auth", None)
    if user and hasattr(user, "pk"):
        actor_id = str(user.pk)
        actor_name = getattr(user, "full_name", None) or str(user)
    else:
        actor_id = "anonymous"
        actor_name = "anonymous"

    # Spoof-resistant client IP (rightmost-untrusted hop); see config/ratelimit.py.
    ip_address = client_ip(request)

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
            "details": details or {},
            "ip_address": ip_address,
        },
    )

    if not persist:
        return

    fields = {
        "action": action,
        "actor": user if user and hasattr(user, "pk") else None,
        "actor_label": actor_name,
        "target_type": target_type,
        "target_id": target_id,
        "details": details or {},
        "ip_address": _valid_ip(ip_address),
        "level": level,
    }
    # on_commit so a rolled-back action leaves no row — the action didn't happen.
    transaction.on_commit(lambda: _persist(**fields))
