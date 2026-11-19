from typing import TYPE_CHECKING, NoReturn

from audit.models import AuditTargetType
from community.validation import Code, InvalidStateTransition, TransitionFailure
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from users.models import User

STATUS_CHANGE_FIELDS = (
    "membership_status",
    "membership_status_changed_at",
    "membership_status_changed_by",
)


def status_change_stamp(by: "User | None") -> dict:
    """Create kwargs that record who set a new account's first status."""
    return {"membership_status_changed_at": timezone.now(), "membership_status_changed_by": by}


class MembershipStatus(models.TextChoices):
    NONE = "none", "none"
    TENTATIVE = "tentative", "tentative"
    ACTIVE_MEMBER = "active_member", "active member"
    ATTENDANCE_PAUSED = "attendance_paused", "attendance paused"
    ARCHIVED = "archived", "archived"
    GUIDELINES_PAUSED = "guidelines_paused", "guidelines paused"


class MembershipEvent(models.TextChoices):
    MARK_TENTATIVE = "mark_tentative", "mark tentative"
    APPROVE = "approve", "approve"
    PROMOTE_ON_CHECK_IN = "promote_on_check_in", "promote on check-in"
    PAUSE_FOR_ATTENDANCE = "pause_for_attendance", "pause for attendance"
    LIFT_ATTENDANCE_PAUSE = "lift_attendance_pause", "lift attendance pause"
    RESTORE_ON_CHECK_IN = "restore_on_check_in", "restore on check-in"
    PAUSE_FOR_GUIDELINES = "pause_for_guidelines", "pause for guidelines"
    LIFT_GUIDELINES_PAUSE = "lift_guidelines_pause", "lift guidelines pause"
    ARCHIVE = "archive", "archive"


# Paused members keep the member role; only active members get full access.
MEMBER_STATUSES = (
    MembershipStatus.ACTIVE_MEMBER,
    MembershipStatus.GUIDELINES_PAUSED,
    MembershipStatus.ATTENDANCE_PAUSED,
)
LIMITED_STATUSES = (MembershipStatus.TENTATIVE, MembershipStatus.ATTENDANCE_PAUSED)
PAUSED_STATUSES = (MembershipStatus.GUIDELINES_PAUSED, MembershipStatus.ATTENDANCE_PAUSED)
# Members not limited to official/club events; a guidelines pause blocks login outright.
FULL_MEMBER_STATUSES = (MembershipStatus.ACTIVE_MEMBER, MembershipStatus.GUIDELINES_PAUSED)
SIGN_IN_STATUSES = (*MEMBER_STATUSES, MembershipStatus.TENTATIVE)
MEMBER_OR_ARCHIVED = (*MEMBER_STATUSES, MembershipStatus.ARCHIVED)
# The admin members screen lists tentative people too, so they can be archived.
MANAGED_STATUSES = (*MEMBER_STATUSES, MembershipStatus.TENTATIVE)

ALLOWED_MEMBERSHIP_TRANSITIONS: dict[tuple[MembershipStatus, MembershipEvent], MembershipStatus] = {
    (MembershipStatus.NONE, MembershipEvent.MARK_TENTATIVE): MembershipStatus.TENTATIVE,
    (MembershipStatus.NONE, MembershipEvent.APPROVE): MembershipStatus.ACTIVE_MEMBER,
    (MembershipStatus.TENTATIVE, MembershipEvent.APPROVE): MembershipStatus.ACTIVE_MEMBER,
    (
        MembershipStatus.TENTATIVE,
        MembershipEvent.PROMOTE_ON_CHECK_IN,
    ): MembershipStatus.ACTIVE_MEMBER,
    (MembershipStatus.TENTATIVE, MembershipEvent.ARCHIVE): MembershipStatus.ARCHIVED,
    (
        MembershipStatus.ACTIVE_MEMBER,
        MembershipEvent.PAUSE_FOR_ATTENDANCE,
    ): MembershipStatus.ATTENDANCE_PAUSED,
    (
        MembershipStatus.ACTIVE_MEMBER,
        MembershipEvent.PAUSE_FOR_GUIDELINES,
    ): MembershipStatus.GUIDELINES_PAUSED,
    (MembershipStatus.ACTIVE_MEMBER, MembershipEvent.ARCHIVE): MembershipStatus.ARCHIVED,
    (
        MembershipStatus.ATTENDANCE_PAUSED,
        MembershipEvent.RESTORE_ON_CHECK_IN,
    ): MembershipStatus.ACTIVE_MEMBER,
    (
        MembershipStatus.ATTENDANCE_PAUSED,
        MembershipEvent.PAUSE_FOR_GUIDELINES,
    ): MembershipStatus.GUIDELINES_PAUSED,
    (MembershipStatus.ATTENDANCE_PAUSED, MembershipEvent.ARCHIVE): MembershipStatus.ARCHIVED,
    (
        MembershipStatus.GUIDELINES_PAUSED,
        MembershipEvent.LIFT_GUIDELINES_PAUSE,
    ): MembershipStatus.ATTENDANCE_PAUSED,
    (MembershipStatus.GUIDELINES_PAUSED, MembershipEvent.ARCHIVE): MembershipStatus.ARCHIVED,
}

_PAUSE_EVENTS = frozenset(
    {
        MembershipEvent.PAUSE_FOR_GUIDELINES,
        MembershipEvent.LIFT_GUIDELINES_PAUSE,
        MembershipEvent.PAUSE_FOR_ATTENDANCE,
    }
)

_EVENT_DEFAULT_TARGET: dict[MembershipEvent, MembershipStatus] = {
    MembershipEvent.MARK_TENTATIVE: MembershipStatus.TENTATIVE,
    MembershipEvent.APPROVE: MembershipStatus.ACTIVE_MEMBER,
    MembershipEvent.PROMOTE_ON_CHECK_IN: MembershipStatus.ACTIVE_MEMBER,
    MembershipEvent.PAUSE_FOR_ATTENDANCE: MembershipStatus.ATTENDANCE_PAUSED,
    MembershipEvent.LIFT_ATTENDANCE_PAUSE: MembershipStatus.ACTIVE_MEMBER,
    MembershipEvent.RESTORE_ON_CHECK_IN: MembershipStatus.ACTIVE_MEMBER,
    MembershipEvent.PAUSE_FOR_GUIDELINES: MembershipStatus.GUIDELINES_PAUSED,
    MembershipEvent.LIFT_GUIDELINES_PAUSE: MembershipStatus.ATTENDANCE_PAUSED,
    MembershipEvent.ARCHIVE: MembershipStatus.ARCHIVED,
}


def _reject(
    user: "User",
    event: MembershipEvent,
    code: str,
    *,
    field: str | None = None,
) -> NoReturn:
    to_status = _EVENT_DEFAULT_TARGET.get(event)
    raise InvalidStateTransition(
        code,
        TransitionFailure(
            action="user_transition_rejected",
            target_type=AuditTargetType.USER,
            target_id=str(user.pk),
            event=str(event),
            from_status=str(user.membership_status),
            to_status=str(to_status) if to_status else None,
        ),
        field=field,
    )


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
    if event == MembershipEvent.PAUSE_FOR_GUIDELINES:
        user.status_before_archive = MembershipStatus.GUIDELINES_PAUSED
        return ["status_before_archive"]
    if event == MembershipEvent.LIFT_GUIDELINES_PAUSE:
        if not user.is_guidelines_paused:
            _reject(user, event, Code.User.INVALID_STATUS_TRANSITION)
        user.status_before_archive = MembershipStatus.ATTENDANCE_PAUSED
        return ["status_before_archive"]
    if user.is_guidelines_paused:
        _reject(user, event, Code.User.GUIDELINES_PAUSED, field="attendance_paused")
    user.status_before_archive = MembershipStatus.ATTENDANCE_PAUSED
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
        code = (
            Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN
            if user.is_attendance_paused
            else Code.User.INVALID_STATUS_TRANSITION
        )
        _reject(user, event, code, field="attendance_paused")
    _reject(user, event, Code.User.INVALID_STATUS_TRANSITION)


def _reject_non_archived(user: "User", event: MembershipEvent) -> NoReturn:
    if event == MembershipEvent.PAUSE_FOR_ATTENDANCE and user.is_guidelines_paused:
        _reject(user, event, Code.User.GUIDELINES_PAUSED, field="attendance_paused")
    if event == MembershipEvent.LIFT_ATTENDANCE_PAUSE:
        code = (
            Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN
            if user.is_attendance_paused
            else Code.User.INVALID_STATUS_TRANSITION
        )
        _reject(user, event, code, field="attendance_paused")
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
    if user.is_archived or user.membership_status == MembershipStatus.ARCHIVED:
        return _handle_archived(user, event, by)
    current = MembershipStatus(user.membership_status)
    target = ALLOWED_MEMBERSHIP_TRANSITIONS.get((current, event))
    if target is None:
        _reject_non_archived(user, event)
    extra = _apply_side_fields(user, event, current)
    return [*extra, *_stamp_status(user, target, by)]
