from typing import TYPE_CHECKING, NoReturn

from audit.models import AuditTargetType
from community.validation import Code, InvalidStateTransition, TransitionFailure
from django.utils import timezone

from users.membership import (
    ALLOWED_MEMBERSHIP_TRANSITIONS,
    PAUSED_STATUSES,
    STATUS_CHANGE_FIELDS,
    MembershipEvent,
    MembershipStatus,
)

if TYPE_CHECKING:
    from users.models import User

_PAUSE_EVENTS = frozenset(
    {
        MembershipEvent.PAUSE_FOR_GUIDELINES,
        MembershipEvent.LIFT_GUIDELINES_PAUSE,
        MembershipEvent.PAUSE_FOR_ATTENDANCE,
    }
)

_EVENT_DEFAULT_TARGET: dict[MembershipEvent, MembershipStatus] = {
    event: target for (_, event), target in ALLOWED_MEMBERSHIP_TRANSITIONS.items()
}
# Always-rejected; kept for audited PATCH refusal payloads.
_EVENT_DEFAULT_TARGET[MembershipEvent.LIFT_ATTENDANCE_PAUSE] = MembershipStatus.ACTIVE_MEMBER


def _reject(
    user: "User",
    event: MembershipEvent,
    code: str,
    *,
    field: str | None = None,
) -> NoReturn:
    raise InvalidStateTransition(
        code,
        TransitionFailure(
            action="user_transition_rejected",
            target_type=AuditTargetType.USER,
            target_id=str(user.pk),
            event=str(event),
            from_status=str(user.membership_status),
            to_status=str(_EVENT_DEFAULT_TARGET[event]),
        ),
        field=field,
    )


def _reject_lift_attendance(user: "User") -> NoReturn:
    code = (
        Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN
        if user.is_attendance_paused
        else Code.User.INVALID_STATUS_TRANSITION
    )
    _reject(user, MembershipEvent.LIFT_ATTENDANCE_PAUSE, code, field="attendance_paused")


def _stamp_status(user: "User", new_status: MembershipStatus, by: "User | None") -> list[str]:
    user.membership_status = new_status
    user.membership_status_changed_at = timezone.now()
    user.membership_status_changed_by = by
    return list(STATUS_CHANGE_FIELDS)


def _unarchive_to(user: "User", fallback: MembershipStatus, by: "User | None") -> list[str]:
    before = user.status_before_archive
    target = MembershipStatus(before) if before in PAUSED_STATUSES else fallback
    user.archived_at = None
    user.status_before_archive = None
    if target == MembershipStatus.ATTENDANCE_PAUSED:
        user.attendance_paused_at = user.attendance_paused_at or timezone.now()
    else:
        user.attendance_paused_at = None
    return [
        "archived_at",
        "attendance_paused_at",
        "status_before_archive",
        *_stamp_status(user, target, by),
    ]


def _park_archived_pause(user: "User", event: MembershipEvent) -> list[str]:
    if user.status_before_archive == MembershipStatus.NONE:
        _reject(user, event, Code.User.INVALID_STATUS_TRANSITION)
    if event == MembershipEvent.LIFT_GUIDELINES_PAUSE and not user.is_guidelines_paused:
        _reject(user, event, Code.User.INVALID_STATUS_TRANSITION)
    if event == MembershipEvent.PAUSE_FOR_ATTENDANCE and user.is_guidelines_paused:
        _reject(user, event, Code.User.GUIDELINES_PAUSED, field="attendance_paused")
    user.status_before_archive = _EVENT_DEFAULT_TARGET[event]
    return ["status_before_archive"]


def _handle_archived(user: "User", event: MembershipEvent, by: "User | None") -> list[str]:
    if event == MembershipEvent.MARK_TENTATIVE:
        return _unarchive_to(user, MembershipStatus.TENTATIVE, by)
    if event == MembershipEvent.APPROVE:
        return _unarchive_to(user, MembershipStatus.ACTIVE_MEMBER, by)
    if event in _PAUSE_EVENTS:
        return _park_archived_pause(user, event)
    if event == MembershipEvent.ARCHIVE:
        _reject(user, event, Code.User.ALREADY_ARCHIVED)
    if event == MembershipEvent.LIFT_ATTENDANCE_PAUSE:
        _reject_lift_attendance(user)
    _reject(user, event, Code.User.INVALID_STATUS_TRANSITION)


def _reject_non_archived(user: "User", event: MembershipEvent) -> NoReturn:
    if event == MembershipEvent.PAUSE_FOR_ATTENDANCE and user.is_guidelines_paused:
        _reject(user, event, Code.User.GUIDELINES_PAUSED, field="attendance_paused")
    if event == MembershipEvent.LIFT_ATTENDANCE_PAUSE:
        _reject_lift_attendance(user)
    _reject(user, event, Code.User.INVALID_STATUS_TRANSITION)


def _apply_side_fields(
    user: "User", event: MembershipEvent, previous: MembershipStatus
) -> list[str]:
    now = timezone.now()
    if event == MembershipEvent.PAUSE_FOR_ATTENDANCE:
        user.attendance_paused_at, user.unpaused_at = now, None
        user.has_joined_whatsapp = False
        return ["attendance_paused_at", "unpaused_at", "has_joined_whatsapp"]
    if event == MembershipEvent.PAUSE_FOR_GUIDELINES:
        user.attendance_paused_at, user.unpaused_at = None, None
        user.has_joined_whatsapp = False
        return ["attendance_paused_at", "unpaused_at", "has_joined_whatsapp"]
    if event == MembershipEvent.LIFT_GUIDELINES_PAUSE:
        user.attendance_paused_at, user.unpaused_at = now, now
        user.has_joined_whatsapp = False
        return ["attendance_paused_at", "unpaused_at", "has_joined_whatsapp"]
    if event == MembershipEvent.RESTORE_ON_CHECK_IN:
        user.attendance_paused_at = None
        user.attendance_grace_notified_at = None
        user.restored_at = now
        return ["attendance_paused_at", "attendance_grace_notified_at", "restored_at"]
    if event == MembershipEvent.ARCHIVE:
        user.archived_at = now
        user.status_before_archive = previous
        user.calendar_token = ""
        return ["archived_at", "status_before_archive", "calendar_token"]
    return []


def transition_membership(user: "User", event: MembershipEvent, *, by: "User | None") -> list[str]:
    """Validate and apply a membership transition, returning changed update_fields."""
    if user.is_archived:
        return _handle_archived(user, event, by)
    try:
        current = MembershipStatus(user.membership_status)
    except ValueError:
        _reject(user, event, Code.User.INVALID_STATUS_TRANSITION)
    target = ALLOWED_MEMBERSHIP_TRANSITIONS.get((current, event))
    if target is None:
        _reject_non_archived(user, event)
    extra = _apply_side_fields(user, event, current)
    return [*extra, *_stamp_status(user, target, by)]
