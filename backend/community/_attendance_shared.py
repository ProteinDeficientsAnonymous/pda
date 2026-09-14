import logging

from config.audit import AuditTarget, AuditTargetType, audit_log

from community._validation import Code, raise_validation


def require_permission(request, action: str, *keys: str) -> None:
    """Allow the request through if the caller holds any one of `keys`."""
    if any(request.auth.has_permission(key) for key in keys):
        return
    audit_log(
        logging.WARNING,
        "permission_denied",
        request,
        persist=False,
        target=AuditTarget(type=AuditTargetType.EVENT, id="", details={"action": action}),
    )
    raise_validation(Code.Perm.DENIED, status_code=403, action=action)
