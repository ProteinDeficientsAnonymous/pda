import pytest
from audit.models import AuditLogEntry
from community.models import Club
from users.models import MembershipStatus
from users.permissions import PermissionKey

from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_user

pytestmark = pytest.mark.django_db
REP_TOOLS = {"list_club_reps", "set_club_reps"}


@pytest.fixture
def manager(db):
    return make_user(PermissionKey.MANAGE_EVENTS)


@pytest.fixture
def book(db):
    return Club.objects.create(name="book club", requirements="")


@pytest.fixture
def a(book):
    user = make_user(first_name="Ada", last_name="A")
    book.reps.add(user)
    return user


def ids(entries):
    return {e["id"] for e in entries}


class TestClubRepTools:
    def test_tools_need_manage_events(self, manager):
        assert not REP_TOOLS & tool_names(make_user())
        assert REP_TOOLS <= tool_names(manager)

    def test_list_club_reps(self, manager, book, a):
        (item,) = run_tool(manager, "list_club_reps")["result"]

        assert item["club_id"] == str(book.id)
        assert item["club_name"] == "book club"
        assert [r["id"] for r in item["reps"]] == [str(a.id)]

    def test_preview_changes_nothing(self, manager, book, a):
        b = make_user()
        preview = run_tool(
            manager, "set_club_reps", club_id=str(book.id), add_member_ids=[str(b.id)]
        )

        assert preview["club"] == {"id": str(book.id), "name": "book club"}
        assert ids(preview["current_reps"]) == {str(a.id)}
        assert ids(preview["resulting_reps"]) == {str(a.id), str(b.id)}
        assert preview["confirm_token"]
        assert set(book.reps.all()) == {a}

    def test_confirm_applies_add_and_remove(self, manager, book, a):
        b = make_user()
        args = {
            "club_id": str(book.id),
            "add_member_ids": [str(b.id)],
            "remove_member_ids": [str(a.id)],
        }
        preview = run_tool(manager, "set_club_reps", **args)
        result = run_tool(manager, "set_club_reps", confirm_token=preview["confirm_token"], **args)

        assert ids(result["reps"]) == {str(b.id)}
        assert set(book.reps.all()) == {b}
        assert AuditLogEntry.objects.filter(action="club_reps_updated").exists()

    def test_add_keeps_archived_existing_rep(self, manager, book, a):
        a.save(update_fields=a.archive(by=None))
        b = make_user()
        args = {"club_id": str(book.id), "add_member_ids": [str(b.id)]}
        preview = run_tool(manager, "set_club_reps", **args)
        run_tool(manager, "set_club_reps", confirm_token=preview["confirm_token"], **args)

        assert set(book.reps.all()) == {a, b}

    def test_token_rejected_after_reps_change_elsewhere(self, manager, book, a):
        b, c = make_user(), make_user()
        args = {"club_id": str(book.id), "add_member_ids": [str(b.id)]}
        preview = run_tool(manager, "set_club_reps", **args)
        book.reps.add(c)

        tool_error(manager, "set_club_reps", confirm_token=preview["confirm_token"], **args)

        assert set(book.reps.all()) == {a, c}

    def test_refuses_non_member_overlap_and_noop(self, manager, book, a):
        gone = make_user(membership_status=MembershipStatus.ARCHIVED)
        club = str(book.id)

        assert "not members" in tool_error(
            manager, "set_club_reps", club_id=club, add_member_ids=[str(gone.id)]
        )
        assert "can't be both" in tool_error(
            manager,
            "set_club_reps",
            club_id=club,
            add_member_ids=[str(a.id)],
            remove_member_ids=[str(a.id)],
        )
        assert "nothing to do" in tool_error(
            manager, "set_club_reps", club_id=club, add_member_ids=[str(a.id)]
        )
        assert "give add_member_ids" in tool_error(manager, "set_club_reps", club_id=club)
