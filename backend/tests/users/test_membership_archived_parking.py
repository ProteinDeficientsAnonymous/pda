import uuid

import pytest
from community.validation import Code, InvalidStateTransition
from django.utils import timezone
from users.models import MembershipEvent, MembershipStatus, User


def _archived(before_archive: MembershipStatus) -> User:
    return User(
        id=uuid.uuid4(),
        phone_number="+13125559998",
        membership_status=MembershipStatus.ARCHIVED,
        archived_at=timezone.now(),
        status_before_archive=before_archive,
    )


@pytest.mark.unit
@pytest.mark.parametrize("before_archive", [MembershipStatus.NONE, MembershipStatus.TENTATIVE])
@pytest.mark.parametrize(
    "event", [MembershipEvent.PAUSE_FOR_GUIDELINES, MembershipEvent.PAUSE_FOR_ATTENDANCE]
)
def test_archived_non_member_cannot_be_parked_into_a_pause(before_archive, event):
    user = _archived(before_archive)
    pause = (
        user.apply_guidelines_pause
        if event == MembershipEvent.PAUSE_FOR_GUIDELINES
        else user.apply_attendance_pause
    )

    with pytest.raises(InvalidStateTransition) as exc_info:
        pause(by=None)

    assert exc_info.value.code == Code.User.INVALID_STATUS_TRANSITION
    assert user.status_before_archive == before_archive


@pytest.mark.unit
def test_archived_tentative_unarchives_back_to_tentative():
    user = _archived(MembershipStatus.TENTATIVE)

    user.mark_tentative(by=None)

    assert user.membership_status == MembershipStatus.TENTATIVE
    assert user.archived_at is None
