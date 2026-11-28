import pytest
from community.models import EventStatus
from users.models import MembershipStatus

from tests._events import make_event
from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_user

TOOL = "archive_member"


@pytest.fixture
def member(db):
    return make_user(first_name="Sam")


@pytest.fixture
def hosted(member):
    return make_event(title="book club", created_by=member)


def _call(user, member, **extra) -> dict:
    return run_tool(user, TOOL, member_id=str(member.pk), **extra)


@pytest.mark.django_db
class TestArchiveMember:
    def test_needs_manage_users(self, member):
        assert TOOL not in tool_names(make_user())
        assert "permission" in tool_error(make_user(), TOOL, member_id=str(member.pk))

    def test_preview_changes_nothing(self, manage_users_user, member, hosted):
        preview = _call(manage_users_user, member)

        assert preview["confirm_token"]
        assert preview["member"]["name"] == member.full_name
        assert [(e["title"], e["outcome"]) for e in preview["events"]] == [("book club", "drafted")]
        member.refresh_from_db()
        assert member.archived_at is None
        hosted.refresh_from_db()
        assert hosted.status != EventStatus.DRAFT

    def test_confirm_archives(self, manage_users_user, member, hosted):
        token = _call(manage_users_user, member)["confirm_token"]

        result = _call(manage_users_user, member, confirm_token=token)

        assert result["archived"] is True
        member.refresh_from_db()
        assert member.membership_status == MembershipStatus.ARCHIVED
        assert member.membership_status_changed_by_id == manage_users_user.pk
        hosted.refresh_from_db()
        assert hosted.status == EventStatus.DRAFT

    def test_refuses_an_already_archived_member(self, manage_users_user, member):
        member.save(update_fields=member.archive(by=manage_users_user))

        assert "already archived" in tool_error(manage_users_user, TOOL, member_id=str(member.pk))

    def test_cannot_archive_yourself(self, manage_users_user):
        token = _call(manage_users_user, manage_users_user)["confirm_token"]

        assert "cannot_delete_self" in tool_error(
            manage_users_user, TOOL, member_id=str(manage_users_user.pk), confirm_token=token
        )
