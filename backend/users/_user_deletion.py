import logging

from community.validation import Code, InvalidStateTransition, TransitionFailure, raise_validation
from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from django.db.models import ProtectedError
from ninja.responses import Status

from users._archive_user import archive_user
from users._management import require_manage_users
from users._management import router as management_router
from users.helpers import is_last_admin
from users.models import MANAGED_STATUSES, MembershipEvent, MembershipStatus, User
from users.schemas import ErrorOut

# Ninja resolves paths before methods, so a second router here would shadow
# /users/search/.
router = management_router


def _raise_already_archived(user: User, user_id: str) -> None:
    raise InvalidStateTransition(
        Code.User.ALREADY_ARCHIVED,
        TransitionFailure(
            action="user_transition_rejected",
            target_type=AuditTargetType.USER,
            target_id=user_id,
            event=MembershipEvent.ARCHIVE,
            from_status=str(user.membership_status),
            to_status=MembershipStatus.ARCHIVED,
        ),
    )


@router.delete(
    "/users/{user_id}/",
    response={204: None, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def delete_user(request, user_id: str):
    require_manage_users(request, "delete_user", user_id)
    try:
        # Archived users are found too, so they get ALREADY_ARCHIVED rather than a 404.
        statuses = (*MANAGED_STATUSES, MembershipStatus.ARCHIVED)
        user = User.objects.filter(membership_status__in=statuses).get(pk=user_id)
    except User.DoesNotExist:
        raise_validation(Code.User.NOT_FOUND, status_code=404)
    if str(user.pk) == str(request.auth.pk):
        raise InvalidStateTransition(
            Code.User.CANNOT_DELETE_SELF,
            TransitionFailure(
                action="user_transition_rejected",
                target_type=AuditTargetType.USER,
                target_id=user_id,
                event=MembershipEvent.ARCHIVE,
                from_status=str(user.membership_status),
                to_status=MembershipStatus.ARCHIVED,
            ),
        )
    if is_last_admin(user):
        raise InvalidStateTransition(
            Code.User.CANNOT_DELETE_LAST_ADMIN,
            TransitionFailure(
                action="user_transition_rejected",
                target_type=AuditTargetType.USER,
                target_id=user_id,
                event=MembershipEvent.ARCHIVE,
                from_status=str(user.membership_status),
                to_status=MembershipStatus.ARCHIVED,
            ),
        )
    if user.archived_at is not None:
        _raise_already_archived(user, user_id)
    previous_status = str(user.membership_status)
    released = archive_user(request, user)
    # Concurrent archive wins the row lock and returns {}; do not audit a no-op as archived.
    if not released:
        _raise_already_archived(user, user_id)
    audit_log(
        logging.WARNING,
        "user_archived",
        request,
        target=AuditTarget(
            type=AuditTargetType.USER,
            id=user_id,
            details={
                "event": MembershipEvent.ARCHIVE,
                "from": previous_status,
                "to": MembershipStatus.ARCHIVED,
                "full_name": user.full_name,
                **released,
            },
        ),
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
    require_manage_users(request, "hard_delete_user", user_id)
    try:
        user = User.objects.members_or_archived().get(pk=user_id)
    except User.DoesNotExist:
        raise_validation(Code.User.NOT_FOUND, status_code=404)
    if str(user.pk) == str(request.auth.pk):
        raise_validation(Code.User.CANNOT_DELETE_SELF, status_code=400)
    if is_last_admin(user):
        raise_validation(Code.User.CANNOT_DELETE_LAST_ADMIN, status_code=400)
    if user.last_login is not None:
        raise_validation(Code.User.CANNOT_HARD_DELETE_LOGGED_IN, status_code=400)
    full_name = user.full_name
    try:
        user.delete()
    except ProtectedError:
        # last_login is not a complete guard: EventComment.author is PROTECT.
        raise_validation(Code.User.CANNOT_HARD_DELETE_LOGGED_IN, status_code=400)
    audit_log(
        logging.WARNING,
        "user_hard_deleted",
        request,
        target=AuditTarget(type=AuditTargetType.USER, id=user_id, details={"full_name": full_name}),
    )
    return Status(204, None)
