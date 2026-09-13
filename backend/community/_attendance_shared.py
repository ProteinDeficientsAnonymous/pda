import logging

from config.audit import AuditTarget, AuditTargetType, audit_log
from users.permissions import PermissionKey

from community._validation import Code, raise_validation


def require_manage_events(request, action: str) -> None:
    if not request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(type=AuditTargetType.EVENT, id="", details={"action": action}),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action=action)
