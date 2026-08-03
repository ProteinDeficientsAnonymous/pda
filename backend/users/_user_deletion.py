import logging

from community._validation import Code, raise_validation
from config.audit import AuditTargetType, audit_log
from config.auth import gated_jwt
from django.utils import timezone
from ninja.responses import Status

from users._helpers import _is_last_admin
from users._management import router as management_router
from users.models import User
from users.permissions import PermissionKey
from users.schemas import ErrorOut

# Ninja resolves paths before methods, so a second router here would shadow
# /users/search/.
router = management_router


@router.delete(
    "/users/{user_id}/",
    response={204: None, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def delete_user(request, user_id: str):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type=AuditTargetType.USER,
            target_id=user_id,
            details={"endpoint": "delete_user", "required_permission": PermissionKey.MANAGE_USERS},
            persist=False,
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="delete_user")
    try:
        user = User.objects.members().get(pk=user_id)
    except User.DoesNotExist:
        raise_validation(Code.User.NOT_FOUND, status_code=404)
    if str(user.pk) == str(request.auth.pk):
        raise_validation(Code.User.CANNOT_DELETE_SELF, status_code=400)
    if _is_last_admin(user):
        raise_validation(Code.User.CANNOT_DELETE_LAST_ADMIN, status_code=400)
    if user.archived_at is not None:
        raise_validation(Code.User.ALREADY_ARCHIVED, status_code=400)
    full_name = user.full_name
    user.archived_at = timezone.now()
    user.save(update_fields=["archived_at"])
    audit_log(
        logging.WARNING,
        "user_archived",
        request,
        target_type=AuditTargetType.USER,
        target_id=user_id,
        details={"full_name": full_name},
    )
    return Status(204, None)


@router.delete(
    "/users/{user_id}/hard/",
    response={204: None, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def hard_delete_user(request, user_id: str):
    """Permanently remove a member who has never logged in.

    Unlike ``delete_user`` (which soft-archives via ``archived_at``), this row is
    gone for good. Restricted to never-logged-in accounts — an approved entry the
    person never actually claimed — so a real member's data is never destroyed.
    """
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type=AuditTargetType.USER,
            target_id=user_id,
            details={
                "endpoint": "hard_delete_user",
                "required_permission": PermissionKey.MANAGE_USERS,
            },
            persist=False,
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="hard_delete_user")
    try:
        user = User.objects.members().get(pk=user_id)
    except User.DoesNotExist:
        raise_validation(Code.User.NOT_FOUND, status_code=404)
    if str(user.pk) == str(request.auth.pk):
        raise_validation(Code.User.CANNOT_DELETE_SELF, status_code=400)
    if _is_last_admin(user):
        raise_validation(Code.User.CANNOT_DELETE_LAST_ADMIN, status_code=400)
    if user.last_login is not None:
        raise_validation(Code.User.CANNOT_HARD_DELETE_LOGGED_IN, status_code=400)
    full_name = user.full_name
    audit_log(
        logging.WARNING,
        "user_hard_deleted",
        request,
        target_type=AuditTargetType.USER,
        target_id=user_id,
        details={"full_name": full_name},
    )
    # Safe because last_login is None: a never-logged-in user has authored no
    # EventComments (author is on_delete=PROTECT), so the cascade can't raise.
    user.delete()
    return Status(204, None)
