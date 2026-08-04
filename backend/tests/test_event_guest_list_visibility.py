import pytest
from community.models import RSVPStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests._public_rsvp_helpers import make_official_event


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(phone_number="+15551234567")


@pytest.fixture
def auth_headers(auth_user):
    refresh = RefreshToken.for_user(auth_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}


@pytest.mark.django_db
class TestEventGuestListVisibility:
    def test_unauthenticated_user_cannot_see_guests(self, api_client):
        """Unsigned-in visitor should get empty guest list even on public event."""
        event = make_official_event()
        response = api_client.get(f"/api/community/events/{event.id}/")
        assert response.status_code == 200
        assert response.json()["guests"] == []

    def test_rsvp_attendee_can_see_guests(self, api_client, db):
        """Signed-in attendee can see guest list."""
        user = User.objects.create_user(phone_number="+15551234567")
        event = make_official_event()
        event.rsvps.create(user=user, status=RSVPStatus.ATTENDING)

        refresh = RefreshToken.for_user(user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}
        response = api_client.get(f"/api/community/events/{event.id}/", **headers)
        assert response.status_code == 200
        guests = response.json()["guests"]
        assert len(guests) > 0
        assert any(g["user_id"] == str(user.id) for g in guests)

    def test_non_rsvp_member_cannot_see_guests(self, api_client, db):
        """Signed-in member who hasn't RSVP'd gets empty guest list."""
        user = User.objects.create_user(phone_number="+15551234567")
        other_user = User.objects.create_user(phone_number="+15559876543")
        event = make_official_event()
        event.rsvps.create(user=other_user, status=RSVPStatus.ATTENDING)

        refresh = RefreshToken.for_user(user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}
        response = api_client.get(f"/api/community/events/{event.id}/", **headers)
        assert response.status_code == 200
        assert response.json()["guests"] == []

    def test_host_can_see_guests(self, api_client, db):
        """Host can see guest list."""
        host = User.objects.create_user(phone_number="+15551234567")
        attendee = User.objects.create_user(phone_number="+15559876543")
        event = make_official_event(created_by=host)
        event.co_hosts.add(host)
        event.rsvps.create(user=attendee, status=RSVPStatus.ATTENDING)

        refresh = RefreshToken.for_user(host)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}
        response = api_client.get(f"/api/community/events/{event.id}/", **headers)
        assert response.status_code == 200
        guests = response.json()["guests"]
        assert len(guests) > 0
        assert any(g["user_id"] == str(attendee.id) for g in guests)
