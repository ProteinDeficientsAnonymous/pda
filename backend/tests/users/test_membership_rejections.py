import uuid

import pytest
from audit.models import AuditTargetType
from community.validation import Code, InvalidStateTransition
from django.utils import timezone
from users._transitions import transition_membership
from users.membership import MembershipEvent, MembershipStatus
from users.models import User

ATTENDANCE_FIELD = "attendance_paused"
INVALID = Code.User.INVALID_STATUS_TRANSITION


def _user(status: MembershipStatus, *, before_archive: MembershipStatus | None = None) -> User:
    archived = status == MembershipStatus.ARCHIVED
    paused_from = before_archive if archived else status
    now = timezone.now()
    return User(
        id=uuid.uuid4(),
        phone_number="+13125559998",
        membership_status=status,
        archived_at=now if archived else None,
        status_before_archive=before_archive,
        attendance_paused_at=now if paused_from == MembershipStatus.ATTENDANCE_PAUSED else None,
    )


def _reject(user: User, event: MembershipEvent) -> InvalidStateTransition:
    with pytest.raises(InvalidStateTransition) as exc_info:
        transition_membership(user, event, by=None)
    return exc_info.value


A = MembershipStatus
E = MembershipEvent


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "before_archive", "event", "code", "field", "to_status"),
    [
        (A.NONE, None, E.RESTORE_ON_CHECK_IN, INVALID, None, A.ACTIVE_MEMBER),
        (A.ACTIVE_MEMBER, None, E.LIFT_GUIDELINES_PAUSE, INVALID, None, A.ATTENDANCE_PAUSED),
        (
            A.GUIDELINES_PAUSED,
            None,
            E.PAUSE_FOR_ATTENDANCE,
            Code.User.GUIDELINES_PAUSED,
            ATTENDANCE_FIELD,
            A.ATTENDANCE_PAUSED,
        ),
        (
            A.ATTENDANCE_PAUSED,
            None,
            E.LIFT_ATTENDANCE_PAUSE,
            Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN,
            ATTENDANCE_FIELD,
            A.ACTIVE_MEMBER,
        ),
        (
            A.ACTIVE_MEMBER,
            None,
            E.LIFT_ATTENDANCE_PAUSE,
            INVALID,
            ATTENDANCE_FIELD,
            A.ACTIVE_MEMBER,
        ),
        (A.ARCHIVED, A.ACTIVE_MEMBER, E.ARCHIVE, Code.User.ALREADY_ARCHIVED, None, A.ARCHIVED),
        (A.ARCHIVED, A.TENTATIVE, E.PROMOTE_ON_CHECK_IN, INVALID, None, A.ACTIVE_MEMBER),
        (A.ARCHIVED, A.ATTENDANCE_PAUSED, E.RESTORE_ON_CHECK_IN, INVALID, None, A.ACTIVE_MEMBER),
        (
            A.ARCHIVED,
            A.ATTENDANCE_PAUSED,
            E.LIFT_ATTENDANCE_PAUSE,
            Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN,
            ATTENDANCE_FIELD,
            A.ACTIVE_MEMBER,
        ),
        (
            A.ARCHIVED,
            A.ACTIVE_MEMBER,
            E.LIFT_ATTENDANCE_PAUSE,
            INVALID,
            ATTENDANCE_FIELD,
            A.ACTIVE_MEMBER,
        ),
        (A.ARCHIVED, A.NONE, E.PAUSE_FOR_GUIDELINES, INVALID, None, A.GUIDELINES_PAUSED),
        (A.ARCHIVED, A.TENTATIVE, E.PAUSE_FOR_ATTENDANCE, INVALID, None, A.ATTENDANCE_PAUSED),
        (A.ARCHIVED, A.ACTIVE_MEMBER, E.LIFT_GUIDELINES_PAUSE, INVALID, None, A.ATTENDANCE_PAUSED),
        (
            A.ARCHIVED,
            A.GUIDELINES_PAUSED,
            E.PAUSE_FOR_ATTENDANCE,
            Code.User.GUIDELINES_PAUSED,
            ATTENDANCE_FIELD,
            A.ATTENDANCE_PAUSED,
        ),
    ],
)
def test_rejection_carries_code_field_and_audit_payload(
    status, before_archive, event, code, field, to_status
):
    user = _user(status, before_archive=before_archive)
    exc = _reject(user, event)
    assert (exc.code, exc.field, exc.status_code) == (code, field, 400)
    assert exc.failure.action == "user_transition_rejected"
    assert exc.failure.target_type == AuditTargetType.USER
    assert exc.failure.target_id == str(user.pk)
    assert (exc.failure.event, exc.failure.from_status, exc.failure.to_status) == (
        str(event),
        str(status),
        str(to_status),
    )


@pytest.mark.unit
def test_corrupt_status_rejects_with_no_field():
    user = _user(A.ACTIVE_MEMBER)
    user.membership_status = "not_a_real_status"
    exc = _reject(user, E.ARCHIVE)
    assert (exc.code, exc.field) == (INVALID, None)
    assert exc.failure.from_status == "not_a_real_status"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("before_archive", "event", "parked"),
    [
        (A.ACTIVE_MEMBER, E.PAUSE_FOR_GUIDELINES, A.GUIDELINES_PAUSED),
        (A.ACTIVE_MEMBER, E.PAUSE_FOR_ATTENDANCE, A.ATTENDANCE_PAUSED),
        (A.ATTENDANCE_PAUSED, E.PAUSE_FOR_GUIDELINES, A.GUIDELINES_PAUSED),
        (A.GUIDELINES_PAUSED, E.LIFT_GUIDELINES_PAUSE, A.ATTENDANCE_PAUSED),
    ],
)
def test_archived_member_pause_is_parked_for_unarchive(before_archive, event, parked):
    user = _user(A.ARCHIVED, before_archive=before_archive)
    assert transition_membership(user, event, by=None) == ["status_before_archive"]
    assert (user.status_before_archive, user.membership_status) == (parked, A.ARCHIVED)
