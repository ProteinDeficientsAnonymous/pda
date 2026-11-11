from datetime import timedelta

import pytest
from django.utils import timezone
from tests._users import make_user
from users.models import MembershipStatus
from users.schemas import UserOut


@pytest.mark.django_db
class TestUserOutPauseFields:
    def test_defaults_to_none(self, test_user):
        out = UserOut.from_user(test_user)
        assert out.attendance_paused_at is None
        assert out.restored_at is None

    def test_serializes_pause_timestamps(self, test_user):
        paused_at = timezone.now()
        test_user.attendance_paused_at = paused_at
        restored_at = paused_at - timedelta(days=30)
        test_user.restored_at = restored_at
        test_user.save(update_fields=["attendance_paused_at", "restored_at"])

        out = UserOut.from_user(test_user)

        assert out.attendance_paused_at == paused_at
        assert out.restored_at == restored_at

    @pytest.mark.parametrize(
        ("fields", "is_paused"),
        [
            ({"membership_status": MembershipStatus.GUIDELINES_PAUSED}, True),
            ({"membership_status": MembershipStatus.ATTENDANCE_PAUSED}, False),
            ({"status_before_archive": MembershipStatus.GUIDELINES_PAUSED}, True),
            ({"status_before_archive": MembershipStatus.ATTENDANCE_PAUSED}, False),
        ],
        ids=["guidelines", "attendance", "archived-guidelines", "archived-attendance"],
    )
    def test_is_paused_is_derived_from_status(self, fields, is_paused):
        if "status_before_archive" in fields:
            fields["archived_at"] = timezone.now()
        assert UserOut.from_user(make_user(**fields)).is_paused is is_paused
