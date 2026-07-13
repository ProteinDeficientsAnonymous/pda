"""Audit logging helper for structured security and admin action logging."""

import logging

from config.ratelimit import client_ip

_audit_logger = logging.getLogger("pda.audit")


def audit_log(  # noqa: PLR0913
    level: int,
    action: str,
    request,
    target_type: str = "",
    target_id: str = "",
    details: dict | None = None,
) -> None:
    """Emit a structured audit log entry.

    Args:
        level: logging.INFO or logging.WARNING
        action: verb describing the event (e.g. 'login_success', 'user_deleted')
        request: the Django/Ninja HttpRequest (used for actor and IP)
        target_type: type of the affected object (e.g. 'user', 'event', 'role')
        target_id: string ID of the affected object
        details: optional context dict (avoid including raw phone numbers or tokens)
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
