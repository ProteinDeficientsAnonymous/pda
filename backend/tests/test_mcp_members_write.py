from datetime import timedelta

import pytest
from community.models import Event, EventStatus
from django.utils import timezone
from users.permissions import PermissionKey

from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_user

TOOL = "set_attendance_pause"


@pytest.fixture
def admin(db):
    return make_user(PermissionKey.MANAGE_USERS, is_member=True)


@pytest.fixture
def member(db):
    return make_user(is_member=True, first_name="Sam")


@pytest.fixture
def hosted(member):
    return Event.objects.create(
        title="book club",
        start_datetime=timezone.now() + timedelta(days=3),
        created_by=member,
        status=EventStatus.ACTIVE,
    )


def _call(user, member, paused=True, **extra) -> dict:
    return run_tool(user, TOOL, member_id=str(member.pk), paused=paused, **extra)


@pytest.mark.django_db
class TestSetAttendancePause:
    def test_needs_manage_users(self, member):
        assert TOOL not in tool_names(make_user(is_member=True))

    def test_preview_changes_nothing(self, admin, member, hosted):
        preview = _call(admin, member)

        assert preview["confirm_token"]
        assert [(e["title"], e["outcome"]) for e in preview["events"]] == [("book club", "drafted")]
        member.refresh_from_db()
        assert member.attendance_paused_at is None

    def test_confirm_pauses(self, admin, member, hosted):
        token = _call(admin, member)["confirm_token"]

        result = _call(admin, member, confirm_token=token)

        assert result["attendance_paused_at"] is not None
        member.refresh_from_db()
        assert member.attendance_paused_at is not None
        assert member.is_paused is False
        hosted.refresh_from_db()
        assert hosted.status == EventStatus.DRAFT

    def test_token_is_bound_to_the_impact(self, admin, member, hosted):
        token = _call(admin, member)["confirm_token"]
        Event.objects.filter(pk=hosted.pk).update(status=EventStatus.CANCELLED)

        assert "fresh preview" in tool_error(
            admin, TOOL, member_id=str(member.pk), paused=True, confirm_token=token
        )

    def test_lifts_the_pause(self, admin, member):
        _call(admin, member, confirm_token=_call(admin, member)["confirm_token"])

        token = _call(admin, member, paused=False)["confirm_token"]
        result = _call(admin, member, paused=False, confirm_token=token)

        assert result["attendance_paused_at"] is None
        member.refresh_from_db()
        assert member.is_member is True

    def test_refuses_a_no_op(self, admin, member):
        assert "isn't attendance-paused" in tool_error(
            admin, TOOL, member_id=str(member.pk), paused=False
        )

    def test_cannot_pause_yourself(self, admin):
        token = _call(admin, admin)["confirm_token"]
        assert "cannot_pause_self" in tool_error(
            admin, TOOL, member_id=str(admin.pk), paused=True, confirm_token=token
        )
