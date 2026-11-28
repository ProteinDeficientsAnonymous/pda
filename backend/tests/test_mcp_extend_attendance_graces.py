import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from users.models import MembershipStatus

from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_user

TOOL = "extend_attendance_graces"


@pytest.fixture
def members(db):
    return [make_user(first_name="Sam"), make_user(first_name="Kai")]


def _ids(*users) -> list[str]:
    return [str(u.pk) for u in users]


def _future(days: int) -> str:
    return (timezone.now() + timedelta(days=days)).date().isoformat()


@pytest.mark.django_db
class TestExtendAttendanceGraces:
    def test_needs_manage_users(self):
        assert TOOL not in tool_names(make_user())

    def test_preview_shows_current_deadlines_and_changes_nothing(self, manage_users_user, members):
        preview = run_tool(
            manage_users_user, TOOL, member_ids=_ids(*members), grace_until=_future(800)
        )

        assert [b["member"]["id"] for b in preview["to_extend"]] == _ids(*members)
        assert all(b["deadline"] for b in preview["to_extend"])
        assert preview["confirm_token"]
        for member in members:
            member.refresh_from_db()
            assert member.attendance_grace_until is None

    def test_confirm_extends_everyone_with_one_token(self, manage_users_user, members):
        args = {"member_ids": _ids(*members), "grace_until": _future(800)}
        token = run_tool(manage_users_user, TOOL, **args)["confirm_token"]

        result = run_tool(manage_users_user, TOOL, confirm_token=token, **args)

        assert [m["id"] for m in result["extended"]] == _ids(*members)
        assert result["failed"] == []
        for member in members:
            member.refresh_from_db()
            assert member.attendance_grace_until.isoformat() == args["grace_until"]

    def test_skips_members_whose_deadline_is_already_later(self, manage_users_user, members):
        members[0].attendance_grace_until = timezone.now().date() + timedelta(days=900)
        members[0].save(update_fields=["attendance_grace_until"])

        preview = run_tool(
            manage_users_user, TOOL, member_ids=_ids(*members), grace_until=_future(800)
        )

        assert [s["id"] for s in preview["skipped"]] == _ids(members[0])
        assert [b["member"]["id"] for b in preview["to_extend"]] == _ids(members[1])

    def test_skips_paused_members(self, manage_users_user, members):
        paused = make_user(membership_status=MembershipStatus.ATTENDANCE_PAUSED)
        preview = run_tool(
            manage_users_user, TOOL, member_ids=_ids(paused, *members), grace_until=_future(800)
        )
        assert [s["id"] for s in preview["skipped"]] == _ids(paused)

    def test_token_is_bound_to_the_date(self, manage_users_user, members):
        ids = _ids(*members)
        token = run_tool(manage_users_user, TOOL, member_ids=ids, grace_until=_future(800))[
            "confirm_token"
        ]
        assert "fresh preview" in tool_error(
            manage_users_user, TOOL, member_ids=ids, grace_until=_future(900), confirm_token=token
        )

    def test_refuses_a_date_that_is_not_in_the_future(self, manage_users_user, members):
        assert "after today" in tool_error(
            manage_users_user, TOOL, member_ids=_ids(*members), grace_until=_future(0)
        )

    def test_rejects_an_unknown_id(self, manage_users_user, members):
        missing = str(uuid.uuid4())
        assert f"no member with id {missing}" in tool_error(
            manage_users_user, TOOL, member_ids=[missing], grace_until=_future(800)
        )

    def test_nothing_to_do_when_everyone_is_skipped(self, manage_users_user):
        paused = make_user(membership_status=MembershipStatus.ATTENDANCE_PAUSED)
        assert "nothing to do" in tool_error(
            manage_users_user, TOOL, member_ids=_ids(paused), grace_until=_future(800)
        )
