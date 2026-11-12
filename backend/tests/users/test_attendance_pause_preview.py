import pytest
from community.models import EventType
from tests._auth import auth_headers_for
from tests._events import make_event, make_rsvp
from users import _attendance_pause_api
from users._attendance_pause import PauseImpact
from users.models import User


def _preview(api_client, user: User, headers: dict):
    return api_client.get(f"/api/auth/users/{user.pk}/attendance-pause-preview/", **headers)


@pytest.mark.django_db
class TestAttendancePausePreview:
    def test_lists_each_event_with_role_and_outcome(
        self, api_client, manage_users_headers, member, other_user
    ):
        drafted = make_event(created_by=member, title="book club")
        kept = make_event(created_by=other_user, event_type=EventType.OFFICIAL, title="meetup")
        make_rsvp(kept, member)

        response = _preview(api_client, member, manage_users_headers)

        assert response.status_code == 200
        events = {e["id"]: e for e in response.json()["events"]}
        assert events[str(kept.pk)]["role"] == "rsvp"
        assert events[str(kept.pk)]["outcome"] == "kept"
        assert events[str(drafted.pk)]["role"] == "hosting"
        assert events[str(drafted.pk)]["outcome"] == "drafted"
        assert events[str(drafted.pk)]["title"] == "book club"

    def test_maps_every_bucket_to_its_role_and_outcome(
        self, api_client, manage_users_headers, member, monkeypatch
    ):
        impact = PauseImpact(
            kept_rsvps=[make_event(title="kept rsvp")],
            removed_rsvps=[make_event(title="removed rsvp")],
            removed_hosting=[make_event(title="removed hosting")],
            drafted_events=[make_event(title="drafted")],
        )
        monkeypatch.setattr(_attendance_pause_api, "pause_impact", lambda *_: impact)

        response = _preview(api_client, member, manage_users_headers)

        pairs = {e["title"]: (e["role"], e["outcome"]) for e in response.json()["events"]}
        assert pairs == {
            "kept rsvp": ("rsvp", "kept"),
            "removed rsvp": ("rsvp", "removed"),
            "removed hosting": ("hosting", "removed"),
            "drafted": ("hosting", "drafted"),
        }

    def test_empty_when_nothing_upcoming(self, api_client, manage_users_headers, member):
        response = _preview(api_client, member, manage_users_headers)
        assert response.json() == {"events": []}

    def test_requires_manage_users(self, api_client, member, other_user):
        response = _preview(api_client, member, auth_headers_for(other_user))
        assert response.status_code == 403

    def test_unknown_user_is_404(self, api_client, manage_users_headers, non_member):
        response = _preview(api_client, non_member, manage_users_headers)
        assert response.status_code == 404
