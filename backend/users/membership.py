from typing import TYPE_CHECKING

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
