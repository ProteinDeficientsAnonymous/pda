from datetime import timedelta

import pytest
from community.models import AttendanceStatus, EventType, RSVPStatus
from django.utils import timezone
from users._restored import ReturnKind

from tests._auth import auth_headers_for
from tests._events import make_event, make_rsvp
from tests._users import make_user

URL = "/api/auth/users/restored/"


def _restored(days_ago: int, *, whatsapp: bool = False, **fields):
    fields.setdefault("is_member", True)
    return make_user(
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


@pytest.mark.django_db
class TestRestoredMembers:
    def test_requires_approve_join_requests(self, api_client):
        response = api_client.get(URL, **auth_headers_for(make_user(is_member=True)))
        assert response.status_code == 403

    def test_lists_restored_newest_first(self, api_client, vettor_headers):
        older = _restored(5, first_name="Older")
        newer = _restored(1, first_name="Newer")
        make_user(is_member=True, first_name="Never")

        rows = api_client.get(URL, **vettor_headers).json()

        assert [r["id"] for r in rows] == [str(newer.id), str(older.id)]
        assert rows[0]["full_name"] == "Newer"
        assert rows[0]["has_joined_whatsapp"] is False
        assert rows[0]["kind"] == ReturnKind.RESTORED

    @pytest.mark.parametrize(
        ("days_ago", "whatsapp", "listed"),
        [(8, True, False), (8, False, True), (6, True, True)],
    )
    def test_clears_after_grace_once_whatsapp_joined(
        self, api_client, vettor_headers, days_ago, whatsapp, listed
    ):
        user = _restored(days_ago, whatsapp=whatsapp)

        ids = [r["id"] for r in api_client.get(URL, **vettor_headers).json()]

        assert (str(user.id) in ids) is listed

    @pytest.mark.parametrize(
        "fields",
        [
            {"archived_at": timezone.now()},
            {"is_paused": True},
            {"is_member": False, "attendance_paused_at": timezone.now()},
        ],
    )
    def test_skips_inactive_members(self, api_client, vettor_headers, fields):
        _restored(1, **fields)

        assert api_client.get(URL, **vettor_headers).json() == []

    def test_shows_last_two_qualifying_events(self, api_client, vettor_headers):
        user = _restored(1)
        _attended(user, "oldest", 30)
        _attended(user, "middle", 20, EventType.CLUB)
        _attended(user, "latest", 10)
        _attended(user, "community", 5, EventType.COMMUNITY)

        [row] = api_client.get(URL, **vettor_headers).json()

        recent = [(e["title"], e["event_type"]) for e in row["recent_events"]]
        assert recent == [("latest", EventType.OFFICIAL), ("middle", EventType.CLUB)]
        assert row["recent_events"][0]["start_datetime"] is not None


def _unpaused(days_ago: int, *, whatsapp: bool = False):
    return make_user(
        is_member=True,
        unpaused_at=timezone.now() - timedelta(days=days_ago),
        has_joined_whatsapp=whatsapp,
    )


def _row(api_client, headers, user):
    return {r["id"]: r for r in api_client.get(URL, **headers).json()}.get(str(user.id))


@pytest.mark.django_db
class TestUnpausedMembers:
    def test_lists_unpaused_as_waiting(self, api_client, vettor_headers):
        row = _row(api_client, vettor_headers, _unpaused(3))

        assert row["kind"] == ReturnKind.UNPAUSED
        assert row["unpaused_at"] is not None
        assert row["came_in_person_at"] is None

    def test_came_in_person_is_first_qualifying_check_in_after_unpause(
        self, api_client, vettor_headers
    ):
        user = _unpaused(10)
        _attended(user, "before unpause", 12)
        _attended(user, "community", 8, EventType.COMMUNITY)
        _attended(user, "first back", 6, EventType.CLUB)
        _attended(user, "second back", 2)

        row = _row(api_client, vettor_headers, user)

        first_back = (timezone.now() - timedelta(days=6)).date().isoformat()
        assert row["came_in_person_at"][:10] == first_back

    def test_check_in_before_unpause_does_not_count(self, api_client, vettor_headers):
        user = _unpaused(3)
        _attended(user, "before unpause", 5)

        assert _row(api_client, vettor_headers, user)["came_in_person_at"] is None

    @pytest.mark.parametrize(
        "case", [(8, True, False), (8, False, True), (6, True, True), (None, True, True)]
    )
    def test_clears_7_days_after_coming_in_once_whatsapp_joined(
        self, api_client, vettor_headers, case
    ):
        came_days_ago, whatsapp, listed = case
        user = _unpaused(20, whatsapp=whatsapp)
        if came_days_ago is not None:
            _attended(user, "back", came_days_ago)

        assert (_row(api_client, vettor_headers, user) is not None) is listed

    def test_sorts_with_restored_newest_first(self, api_client, vettor_headers):
        restored = _restored(2)
        unpaused = _unpaused(1)

        ids = [r["id"] for r in api_client.get(URL, **vettor_headers).json()]

        assert ids == [str(unpaused.id), str(restored.id)]
