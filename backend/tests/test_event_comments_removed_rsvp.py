import json

import pytest
from community.models import Event, EventRSVP, RSVPStatus
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
class TestRemovedRsvperComments:
    def test_removed_rsvper_cannot_read_or_post(self, api_client, event):
        user = _rsvper(event, RSVPStatus.REMOVED)
        body = _list(api_client, event, user).json()
        assert body["can_post"] is False
        assert body["items"] == []
        assert body["cannot_post_reason"] == "rsvp_required"
        response = _post(api_client, event, user)
        assert response.status_code == 403
        assert response.json()["detail"][0]["code"] == "comment.rsvp_required"

    @pytest.mark.parametrize(
        "status",
        [RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.WAITLISTED, RSVPStatus.CANT_GO],
    )
    def test_other_rsvpers_can_post(self, api_client, event, status):
        user = _rsvper(event, status)
        assert _list(api_client, event, user).json()["can_post"] is True
        response = _post(api_client, event, user)
        assert response.status_code == 201, response.content
