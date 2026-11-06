from datetime import timedelta

import pytest
from community.models import Event, EventRSVP, EventType, RSVPStatus
from django.utils import timezone
from tests._auth import auth_headers_for
from users.models import User


def _event(creator: User, event_type=EventType.COMMUNITY, title="potluck") -> Event:
    return Event.objects.create(
        title=title,
        event_type=event_type,
        start_datetime=timezone.now() + timedelta(days=3),
        created_by=creator,
    )


def _preview(api_client, user: User, headers: dict):
    return api_client.get(f"/api/auth/users/{user.pk}/attendance-pause-preview/", **headers)


@pytest.mark.django_db
class TestAttendancePausePreview:
    def test_lists_each_event_with_role_and_outcome(
        self, api_client, manage_users_headers, member, other_user
    ):
        drafted = _event(member, title="book club")
        kept = _event(other_user, EventType.OFFICIAL, title="meetup")
        EventRSVP.objects.create(event=kept, user=member, status=RSVPStatus.ATTENDING)

        response = _preview(api_client, member, manage_users_headers)

        assert response.status_code == 200
        events = {e["id"]: e for e in response.json()["events"]}
        assert events[str(kept.pk)]["role"] == "rsvp"
        assert events[str(kept.pk)]["outcome"] == "kept"
        assert events[str(drafted.pk)]["role"] == "hosting"
        assert events[str(drafted.pk)]["outcome"] == "drafted"
        assert events[str(drafted.pk)]["title"] == "book club"

    def test_empty_when_nothing_upcoming(self, api_client, manage_users_headers, member):
        response = _preview(api_client, member, manage_users_headers)
        assert response.json() == {"events": []}

    def test_requires_manage_users(self, api_client, member, other_user):
        response = _preview(api_client, member, auth_headers_for(other_user))
        assert response.status_code == 403

    def test_unknown_user_is_404(self, api_client, manage_users_headers, non_member):
        response = _preview(api_client, non_member, manage_users_headers)
        assert response.status_code == 404
