import pytest
from community.models import Event, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso


@pytest.fixture
def rsvp_event(db, test_user):
    return Event.objects.create(
        title="RSVP Event",
        description="An event with RSVPs enabled",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        location="Community Space",
        rsvp_enabled=True,
        created_by=test_user,
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        phone_number="+12025550302",
        password="otherpass",
        first_name="Other",
        last_name="Member",
    )


@pytest.fixture
def other_headers(other_user):
    refresh = RefreshToken.for_user(other_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestCreateEventWithCohosts:
    def test_create_event_with_cohosts_creates_pending_invite(
        self, api_client, auth_headers, other_user
    ):
        # With the invite-approval flow (#363), passing ``co_host_ids`` queues
        # a PENDING invite — the user is NOT in event.co_hosts until they accept.
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Cohost Event",
                "start_datetime": future_iso(days=60),
                "end_datetime": future_iso(days=60, hours=2),
                "co_host_ids": [str(other_user.pk)],
            },
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["co_host_ids"] == []
        assert any(inv["user_id"] == str(other_user.pk) for inv in data["pending_cohost_invites"])

    def test_create_event_with_rsvp_enabled(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "RSVP Event",
                "start_datetime": future_iso(days=60),
                "end_datetime": future_iso(days=60, hours=2),
                "rsvp_enabled": True,
            },
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["rsvp_enabled"] is True

    def test_update_event_toggle_rsvp(self, api_client, auth_headers, rsvp_event):
        response = api_client.patch(
            f"/api/community/events/{rsvp_event.id}/",
            {"rsvp_enabled": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["rsvp_enabled"] is False

    def test_cohost_sees_guest_phones(
        self, api_client, auth_headers, other_user, other_headers, test_user
    ):
        # Create event inviting other_user as co-host (PENDING under the
        # invite-approval flow), then have them accept so they're an actual
        # co-host with phone visibility.
        create_resp = api_client.post(
            "/api/community/events/",
            {
                "title": "Cohost Phone Test",
                "start_datetime": future_iso(days=90),
                "end_datetime": future_iso(days=90, hours=2),
                "rsvp_enabled": True,
                "co_host_ids": [str(other_user.pk)],
            },
            content_type="application/json",
            **auth_headers,
        )
        assert create_resp.status_code == 201
        event_id = create_resp.json()["id"]
        invite_id = create_resp.json()["pending_cohost_invites"][0]["id"]

        # other_user accepts the invite → becomes an accepted co-host.
        accept_resp = api_client.post(
            f"/api/community/events/{event_id}/cohost-invites/{invite_id}/accept/",
            **other_headers,
        )
        assert accept_resp.status_code == 200

        # Creator RSVPs.
        api_client.post(
            f"/api/community/events/{event_id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )

        # Co-host fetches — should see phones.
        response = api_client.get(f"/api/community/events/{event_id}/", **other_headers)
        assert response.status_code == 200
        guests = response.json()["guests"]
        assert len(guests) == 1
        assert guests[0]["phone"] == test_user.phone_number
