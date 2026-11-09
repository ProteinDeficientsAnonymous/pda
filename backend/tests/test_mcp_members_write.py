import uuid

import pytest
from community.models import Event, EventStatus
from users.models import MembershipStatus

from tests._events import make_event
from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_user

TOOL = "set_attendance_pause"


@pytest.fixture
def member(db):
    return make_user(first_name="Sam")


@pytest.fixture
def hosted(member):
    return make_event(title="book club", created_by=member)


def _call(user, member, paused=True, **extra) -> dict:
    return run_tool(user, TOOL, member_id=str(member.pk), paused=paused, **extra)


@pytest.mark.django_db
class TestSetAttendancePause:
    def test_needs_manage_users(self):
        assert TOOL not in tool_names(make_user())

    @pytest.mark.parametrize("row_exists", [False, True])
    def test_rejects_an_unknown_or_non_member_id(self, manage_users_user, row_exists):
        missing = str(
            make_user(membership_status=MembershipStatus.PUBLIC_RSVPER).pk
            if row_exists
            else uuid.uuid4()
        )
        assert f"no member with id {missing}" in tool_error(
            manage_users_user, TOOL, member_id=missing, paused=True
        )

    def test_preview_changes_nothing(self, manage_users_user, member, hosted):
        preview = _call(manage_users_user, member)

        assert preview["confirm_token"]
        assert [(e["title"], e["outcome"]) for e in preview["events"]] == [("book club", "drafted")]
        member.refresh_from_db()
        assert member.attendance_paused_at is None

    def test_confirm_pauses(self, manage_users_user, member, hosted):
        token = _call(manage_users_user, member)["confirm_token"]

        result = _call(manage_users_user, member, confirm_token=token)

        assert result["attendance_paused_at"] is not None
        member.refresh_from_db()
        assert member.attendance_paused_at is not None
        assert member.is_paused is False
        hosted.refresh_from_db()
        assert hosted.status == EventStatus.DRAFT

    def test_token_is_bound_to_the_impact(self, manage_users_user, member, hosted):
        token = _call(manage_users_user, member)["confirm_token"]
        Event.objects.filter(pk=hosted.pk).update(status=EventStatus.CANCELLED)

        assert "fresh preview" in tool_error(
            manage_users_user, TOOL, member_id=str(member.pk), paused=True, confirm_token=token
        )

    def test_lifts_the_pause(self, manage_users_user, member):
        _call(
            manage_users_user,
            member,
            confirm_token=_call(manage_users_user, member)["confirm_token"],
        )

        token = _call(manage_users_user, member, paused=False)["confirm_token"]
        result = _call(manage_users_user, member, paused=False, confirm_token=token)

        assert result["attendance_paused_at"] is None
        member.refresh_from_db()
        assert member.is_member is True

    def test_refuses_a_no_op(self, manage_users_user, member):
        assert "isn't attendance-paused" in tool_error(
            manage_users_user, TOOL, member_id=str(member.pk), paused=False
        )

    def test_cannot_pause_yourself(self, manage_users_user):
        token = _call(manage_users_user, manage_users_user)["confirm_token"]
        assert "cannot_pause_self" in tool_error(
            manage_users_user,
            TOOL,
            member_id=str(manage_users_user.pk),
            paused=True,
            confirm_token=token,
        )
