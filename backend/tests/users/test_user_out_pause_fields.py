from datetime import timedelta

import pytest
from django.utils import timezone
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
