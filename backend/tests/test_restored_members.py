from datetime import timedelta

import pytest
from community.models import AttendanceStatus, EventType, RSVPStatus
from django.utils import timezone
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._events import make_event, make_rsvp
from tests._users import make_user

URL = "/api/auth/users/restored/"


def _restored(days_ago: int, *, whatsapp: bool = False, **fields):
    return make_user(
        is_member=True,
        restored_at=timezone.now() - timedelta(days=days_ago),
        has_joined_whatsapp=whatsapp,
        **fields,
    )


def _attended(user, title: str, days_ago: int, event_type=EventType.OFFICIAL):
    event = make_event(
        title=title,
        event_type=event_type,
        start_datetime=timezone.now() - timedelta(days=days_ago),
    )
    make_rsvp(event, user, RSVPStatus.ATTENDING, attendance=AttendanceStatus.ATTENDED)


@pytest.fixture
def approver_headers(db):
    return auth_headers_for(make_user(PermissionKey.APPROVE_JOIN_REQUESTS))


@pytest.mark.django_db
class TestRestoredMembers:
    def test_requires_approve_join_requests(self, api_client):
        response = api_client.get(URL, **auth_headers_for(make_user(is_member=True)))
        assert response.status_code == 403

    def test_lists_restored_newest_first(self, api_client, approver_headers):
        older = _restored(5, first_name="Older")
        newer = _restored(1, first_name="Newer")
        make_user(is_member=True, first_name="Never")

        rows = api_client.get(URL, **approver_headers).json()

        assert [r["id"] for r in rows] == [str(newer.id), str(older.id)]
        assert rows[0]["full_name"] == "Newer"
        assert rows[0]["has_joined_whatsapp"] is False

    @pytest.mark.parametrize(
        ("days_ago", "whatsapp", "listed"),
        [(8, True, False), (8, False, True), (6, True, True)],
    )
    def test_clears_after_grace_once_whatsapp_joined(
        self, api_client, approver_headers, days_ago, whatsapp, listed
    ):
        user = _restored(days_ago, whatsapp=whatsapp)

        ids = [r["id"] for r in api_client.get(URL, **approver_headers).json()]

        assert (str(user.id) in ids) is listed

    def test_skips_archived(self, api_client, approver_headers):
        _restored(1, archived_at=timezone.now())

        assert api_client.get(URL, **approver_headers).json() == []

    def test_shows_last_two_qualifying_events(self, api_client, approver_headers):
        user = _restored(1)
        _attended(user, "oldest", 30)
        _attended(user, "middle", 20, EventType.CLUB)
        _attended(user, "latest", 10)
        _attended(user, "community", 5, EventType.COMMUNITY)

        [row] = api_client.get(URL, **approver_headers).json()

        assert [e["title"] for e in row["recent_events"]] == ["latest", "middle"]
        assert row["recent_events"][0]["start_datetime"] is not None
