import pytest
from community.models import RSVPStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._public_rsvp_helpers import make_official_event


@pytest.fixture
def other_user(db):
    return User.objects.create_user(phone_number="+15559876543")


@pytest.fixture
def other_auth_headers(other_user):
    refresh = RefreshToken.for_user(other_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}


@pytest.fixture
def event_manager_headers(db):
    user = User.objects.create_user(phone_number="+15550001111")
    role = Role.objects.create(name="event_manager", permissions=[PermissionKey.MANAGE_EVENTS])
    user.roles.add(role)
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}


@pytest.mark.django_db
class TestEventGuestListVisibility:
    def test_unauthenticated_user_cannot_see_guests(self, api_client):
        event = make_official_event()
        response = api_client.get(f"/api/community/events/{event.id}/")
        assert response.status_code == 200
        assert response.json()["guests"] == []

    def test_rsvp_attendee_can_see_guests(self, api_client, test_user, auth_headers):
        event = make_official_event()
        event.rsvps.create(user=test_user, status=RSVPStatus.ATTENDING)

        response = api_client.get(f"/api/community/events/{event.id}/", **auth_headers)
        assert response.status_code == 200
        guests = response.json()["guests"]
        assert len(guests) > 0
        assert any(g["user_id"] == str(test_user.id) for g in guests)

    def test_non_rsvp_member_cannot_see_guests(
        self, api_client, test_user, auth_headers, other_user
    ):
        event = make_official_event()
        event.rsvps.create(user=other_user, status=RSVPStatus.ATTENDING)

        response = api_client.get(f"/api/community/events/{event.id}/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["guests"] == []

    def test_host_can_see_guests(self, api_client, test_user, auth_headers, other_user):
        event = make_official_event(created_by=test_user)
        event.co_hosts.add(test_user)
        event.rsvps.create(user=other_user, status=RSVPStatus.ATTENDING)

        response = api_client.get(f"/api/community/events/{event.id}/", **auth_headers)
        assert response.status_code == 200
        guests = response.json()["guests"]
        assert len(guests) > 0
        assert any(g["user_id"] == str(other_user.id) for g in guests)

    def test_event_manager_can_see_guests_without_rsvp(
        self, api_client, event_manager_headers, other_user
    ):
        event = make_official_event()
        event.rsvps.create(user=other_user, status=RSVPStatus.ATTENDING)

        response = api_client.get(f"/api/community/events/{event.id}/", **event_manager_headers)
        assert response.status_code == 200
        guests = response.json()["guests"]
        assert len(guests) > 0
        assert any(g["user_id"] == str(other_user.id) for g in guests)

    def test_cant_go_rsvp_can_see_guests(self, api_client, test_user, auth_headers, other_user):
        event = make_official_event()
        event.rsvps.create(user=test_user, status=RSVPStatus.CANT_GO)
        event.rsvps.create(user=other_user, status=RSVPStatus.ATTENDING)

        response = api_client.get(f"/api/community/events/{event.id}/", **auth_headers)
        assert response.status_code == 200
        guests = response.json()["guests"]
        assert any(g["user_id"] == str(other_user.id) for g in guests)

    def test_removed_rsvp_cannot_see_guests(self, api_client, test_user, auth_headers, other_user):
        event = make_official_event()
        event.rsvps.create(user=test_user, status=RSVPStatus.REMOVED)
        event.rsvps.create(user=other_user, status=RSVPStatus.ATTENDING)

        response = api_client.get(f"/api/community/events/{event.id}/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["guests"] == []

    def test_guest_list_ordered_going_maybe_cant_go_waitlisted(
        self, api_client, test_user, auth_headers
    ):
        event = make_official_event(created_by=test_user)
        event.co_hosts.add(test_user)
        waitlisted = User.objects.create_user(phone_number="+15551110001")
        cant_go = User.objects.create_user(phone_number="+15551110002")
        maybe = User.objects.create_user(phone_number="+15551110003")
        going = User.objects.create_user(phone_number="+15551110004")
        # created out of order to prove sort isn't relying on insertion/DB order
        event.rsvps.create(user=waitlisted, status=RSVPStatus.WAITLISTED)
        event.rsvps.create(user=cant_go, status=RSVPStatus.CANT_GO)
        event.rsvps.create(user=maybe, status=RSVPStatus.MAYBE)
        event.rsvps.create(user=going, status=RSVPStatus.ATTENDING)

        response = api_client.get(f"/api/community/events/{event.id}/", **auth_headers)
        assert response.status_code == 200
        statuses = [g["status"] for g in response.json()["guests"]]
        assert statuses == [
            RSVPStatus.ATTENDING,
            RSVPStatus.MAYBE,
            RSVPStatus.CANT_GO,
            RSVPStatus.WAITLISTED,
        ]
