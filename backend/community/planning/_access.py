import logging

from config.audit import AuditTarget, audit_log
from users.permissions import PermissionKey

from community.validation import Code, raise_validation


def can_manage_planning(user) -> bool:
    return user.has_permission(PermissionKey.MANAGE_EVENT_PLANNING)


def can_view_planning(user) -> bool:
    return user.has_permission(PermissionKey.VIEW_EVENT_PLANNING) or can_manage_planning(user)


def _deny(request, action: str, permission: PermissionKey) -> None:
    audit_log(
        logging.WARNING,
        "permission_denied",
        request,
        persist=False,
        target=AuditTarget(details={"endpoint": action, "required_permission": permission}),
    )
    raise_validation(Code.Perm.DENIED, status_code=403, action=action)


def require_view(request, action: str) -> None:
    if not can_view_planning(request.auth):
        _deny(request, action, PermissionKey.VIEW_EVENT_PLANNING)


def require_manage(request, action: str) -> None:
    if not can_manage_planning(request.auth):
        _deny(request, action, PermissionKey.MANAGE_EVENT_PLANNING)


def require_manage_or(request, action: str, allowed: bool) -> None:
    if not (allowed or can_manage_planning(request.auth)):
        _deny(request, action, PermissionKey.MANAGE_EVENT_PLANNING)
