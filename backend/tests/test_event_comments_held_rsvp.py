import json

import pytest
from community.models import HELD_RSVP_STATUSES, Event, EventRSVP, RSVPStatus
from users.models import User

from tests._auth import auth_headers_for
from tests._time import future_iso


@pytest.fixture
def event(db, test_user):
    return Event.objects.create(
        title="Test Event",
        start_datetime=future_iso(days=30),
        created_by=test_user,
    )


def _rsvper(event: Event, status: RSVPStatus) -> User:
    user = User.objects.create_user(
        phone_number="+12025550777", password="rsvperpass", first_name="Rsvper"
    )
    EventRSVP.objects.create(event=event, user=user, status=status)
    return user


def _list(api_client, event: Event, user: User):
    return api_client.get(f"/api/community/events/{event.id}/comments/", **auth_headers_for(user))


def _post(api_client, event: Event, user: User):
    return api_client.post(
        f"/api/community/events/{event.id}/comments/",
        data=json.dumps({"body": "hi"}),
        content_type="application/json",
        **auth_headers_for(user),
    )


@pytest.mark.django_db
class TestCommentsRequireHeldRsvp:
    @pytest.mark.parametrize("status", [RSVPStatus.CANT_GO, RSVPStatus.REMOVED])
    def test_released_rsvper_cannot_post(self, api_client, event, status):
        user = _rsvper(event, status)
        body = _list(api_client, event, user).json()
        assert body["can_post"] is False
        assert body["cannot_post_reason"] == "rsvp_required"
        response = _post(api_client, event, user)
        assert response.status_code == 403
        assert response.json()["detail"][0]["code"] == "comment.rsvp_required"

    @pytest.mark.parametrize("status", HELD_RSVP_STATUSES)
    def test_held_rsvper_can_post(self, api_client, event, status):
        user = _rsvper(event, status)
        assert _list(api_client, event, user).json()["can_post"] is True
        response = _post(api_client, event, user)
        assert response.status_code == 201, response.content

    def test_held_statuses_cover_attending_maybe_waitlisted(self):
        assert set(HELD_RSVP_STATUSES) == {
            RSVPStatus.ATTENDING,
            RSVPStatus.MAYBE,
            RSVPStatus.WAITLISTED,
        }
