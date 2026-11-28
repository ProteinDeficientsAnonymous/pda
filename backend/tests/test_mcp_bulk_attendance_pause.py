import pytest
from community.models import Event, EventStatus
from users.models import MembershipStatus

from tests._events import make_event
from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_user

TOOL = "set_attendance_pauses"


@pytest.fixture
def members(db):
    return [make_user(first_name="Sam"), make_user(first_name="Kai")]


def _ids(*users) -> list[str]:
    return [str(u.pk) for u in users]


@pytest.mark.django_db
class TestSetAttendancePauses:
    def test_needs_manage_users(self):
        assert TOOL not in tool_names(make_user())

    def test_preview_lists_the_batch_and_changes_nothing(self, manage_users_user, members):
        make_event(title="book club", created_by=members[0])

        preview = run_tool(manage_users_user, TOOL, member_ids=_ids(*members))

        assert preview["confirm_token"]
        assert [b["member"]["id"] for b in preview["to_pause"]] == _ids(*members)
        assert [e["outcome"] for e in preview["to_pause"][0]["events"]] == ["drafted"]
        for member in members:
            member.refresh_from_db()
            assert member.attendance_paused_at is None

    def test_confirm_pauses_everyone_with_one_token(self, manage_users_user, members):
        ids = _ids(*members)
        token = run_tool(manage_users_user, TOOL, member_ids=ids)["confirm_token"]

        result = run_tool(manage_users_user, TOOL, member_ids=ids, confirm_token=token)

        assert len(result["paused"]) == 2
        assert result["failed"] == []
        for member in members:
            member.refresh_from_db()
            assert member.membership_status == MembershipStatus.ATTENDANCE_PAUSED

    def test_already_paused_members_are_skipped(self, manage_users_user, members):
        ids = _ids(*members)
        first = run_tool(manage_users_user, TOOL, member_ids=ids[:1])["confirm_token"]
        run_tool(manage_users_user, TOOL, member_ids=ids[:1], confirm_token=first)

        preview = run_tool(manage_users_user, TOOL, member_ids=ids)

        assert [s["id"] for s in preview["skipped"]] == ids[:1]
        assert [b["member"]["id"] for b in preview["to_pause"]] == ids[1:]

    def test_token_is_bound_to_the_batch(self, manage_users_user, members):
        hosted = make_event(title="book club", created_by=members[0])
        ids = _ids(*members)
        token = run_tool(manage_users_user, TOOL, member_ids=ids)["confirm_token"]
        Event.objects.filter(pk=hosted.pk).update(status=EventStatus.CANCELLED)

        assert "fresh preview" in tool_error(
            manage_users_user, TOOL, member_ids=ids, confirm_token=token
        )
        assert "fresh preview" in tool_error(
            manage_users_user, TOOL, member_ids=ids[:1], confirm_token=token
        )

    def test_refuses_your_own_id(self, manage_users_user, members):
        assert "yourself" in tool_error(
            manage_users_user, TOOL, member_ids=_ids(manage_users_user, *members)
        )

    def test_refuses_more_than_fifty(self, manage_users_user):
        ids = [str(make_user().pk) for _ in range(51)]
        assert tool_error(manage_users_user, TOOL, member_ids=ids)
