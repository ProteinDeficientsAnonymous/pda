import uuid
from datetime import timedelta

import pytest
from community.models import Club, Event, EventType
from django.utils import timezone
from users.permissions import PermissionKey

from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_user

pytestmark = pytest.mark.django_db
WRITE_TOOLS = {"save_club", "delete_club"}
CLUB_WALK = {"title": "book club", "start_datetime": "2099-11-07T11:00", "event_type": "club"}


@pytest.fixture
def manager(db):
    return make_user(PermissionKey.MANAGE_EVENTS)


@pytest.fixture
def host(db):
    return make_user(PermissionKey.TAG_CLUB_EVENT)


@pytest.fixture
def book(db):
    return Club.objects.create(name="book club", requirements="read along")


class TestClubTools:
    def test_writes_need_manage_events(self, manager):
        assert "list_clubs" in tool_names(make_user())
        assert not WRITE_TOOLS & tool_names(make_user())
        assert WRITE_TOOLS <= tool_names(manager)

    def test_list(self, book):
        assert run_tool(make_user(), "list_clubs") == {
            "result": [{"id": str(book.id), "name": "book club", "requirements": "read along"}]
        }

    def test_save_creates(self, manager):
        club = run_tool(manager, "save_club", name="doggie meetup club", requirements="dog parents")

        assert (club["name"], club["requirements"]) == ("doggie meetup club", "dog parents")
        assert Club.objects.get().name == "doggie meetup club"

    def test_save_new_needs_name(self, manager):
        assert tool_error(manager, "save_club", requirements="x") == "a new club needs a name"

    def test_save_updates_only_given_fields(self, manager, book):
        run_tool(manager, "save_club", club_id=str(book.id), name="books")

        book.refresh_from_db()
        assert (book.name, book.requirements) == ("books", "read along")

    def test_save_can_clear_requirements(self, manager, book):
        run_tool(manager, "save_club", club_id=str(book.id), requirements="")

        book.refresh_from_db()
        assert (book.name, book.requirements) == ("book club", "")

    def test_save_rejects_duplicate_name(self, manager, book):
        assert tool_error(manager, "save_club", name="Book Club")

    def test_unknown_club(self, manager):
        missing = uuid.uuid4()
        assert tool_error(manager, "save_club", club_id=str(missing), name="x") == (
            f"no club with id {missing}"
        )

    def test_delete_asks_first(self, manager, book):
        preview = run_tool(manager, "delete_club", club_id=str(book.id))

        assert preview["club"]["name"] == "book club"
        assert Club.objects.exists()

        result = run_tool(
            manager, "delete_club", club_id=str(book.id), confirm_token=preview["confirm_token"]
        )

        assert result["deleted"]["name"] == "book club"
        assert not Club.objects.exists()


class TestEventClub:
    def test_create_club_event_by_club_name(self, host, book):
        summary = run_tool(host, "create_event", fields={**CLUB_WALK, "club": "Book Club"})

        assert summary["club"] == "book club"
        assert Event.objects.get(pk=summary["id"]).club == book

    def test_club_event_needs_a_club(self, host):
        assert "club" in tool_error(host, "create_event", fields=CLUB_WALK)

    def test_unknown_club_lists_valid_ones(self, host, book):
        error = tool_error(host, "create_event", fields={**CLUB_WALK, "club": "chess"})

        assert error == "unknown club: chess. valid clubs: book club"

    def test_update_changes_club(self, host, book):
        movie = Club.objects.create(name="movie club")
        event = Event.objects.create(
            title="meetup",
            event_type=EventType.CLUB,
            club=book,
            start_datetime=timezone.now() + timedelta(days=10),
            created_by=host,
        )

        preview = run_tool(
            host, "update_event", event=str(event.id), changes={"club": "movie club"}
        )
        assert preview["changes"]["club"] == {"before": "book club", "after": "movie club"}
        run_tool(
            host,
            "update_event",
            event=str(event.id),
            changes={"club": "movie club"},
            confirm_token=preview["confirm_token"],
        )

        event.refresh_from_db()
        assert event.club == movie
