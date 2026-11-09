import json

import pytest
from community.models import Event, EventComment, EventRSVP, EventType, RSVPStatus
from django.utils import timezone
from users.models import User

from tests._auth import auth_headers_for
from tests._time import future_iso


@pytest.fixture
def attendance_paused_user(db):
    return User.objects.create_user(
        phone_number="+12025550930",
        password="pausedpass",
        first_name="Paused",
        is_member=False,
        attendance_paused_at=timezone.now(),
    )


def _event_with_released_rsvp(host: User, user: User, event_type: EventType) -> Event:
    event = Event.objects.create(
        title="Event",
        start_datetime=future_iso(days=10),
        created_by=host,
        event_type=event_type,
    )
    EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.CANT_GO)
    return event


def _post(api_client, event: Event, user: User, path: str = "comments/"):
    return api_client.post(
        f"/api/community/events/{event.id}/{path}",
        data=json.dumps({"body": "hi"}),
        content_type="application/json",
        **auth_headers_for(user),
    )


@pytest.mark.django_db
class TestLimitedUserComments:
    def test_paused_user_cannot_post_on_community_event_they_were_released_from(
        self, api_client, test_user, attendance_paused_user
    ):
        event = _event_with_released_rsvp(test_user, attendance_paused_user, EventType.COMMUNITY)
        response = _post(api_client, event, attendance_paused_user)
        assert response.status_code == 403
        assert response.json()["detail"][0]["code"] == "comment.rsvp_required"

    def test_paused_user_cannot_reply_on_community_event(
        self, api_client, test_user, attendance_paused_user
    ):
        event = _event_with_released_rsvp(test_user, attendance_paused_user, EventType.COMMUNITY)
        parent = EventComment.objects.create(event=event, author=test_user, body="host")
        response = _post(
            api_client, event, attendance_paused_user, f"comments/{parent.id}/replies/"
        )
        assert response.status_code == 403

    def test_paused_user_cannot_read_community_event_comments(
        self, api_client, test_user, attendance_paused_user
    ):
        event = _event_with_released_rsvp(test_user, attendance_paused_user, EventType.COMMUNITY)
        EventComment.objects.create(event=event, author=test_user, body="host")
        response = api_client.get(
            f"/api/community/events/{event.id}/comments/",
            **auth_headers_for(attendance_paused_user),
        )
        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["can_post"] is False

    def test_paused_user_can_post_on_official_event_they_rsvpd_to(
        self, api_client, test_user, attendance_paused_user
    ):
        event = _event_with_released_rsvp(test_user, attendance_paused_user, EventType.OFFICIAL)
        response = _post(api_client, event, attendance_paused_user)
        assert response.status_code == 201, response.content
