"""Tests for event RSVP endpoints and event detail GET."""

import pytest
from community._validation import Code
from community.models import Event, EventRSVP, RSVPStatus

from tests._asserts import assert_error_code
from tests.conftest import future_iso

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
def no_rsvp_event(db):
    return Event.objects.create(
        title="No RSVP Event",
        start_datetime=future_iso(days=31),
        end_datetime=future_iso(days=31, hours=2),
        rsvp_enabled=False,
    )


@pytest.fixture
def other_user(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+12025550302",
        password="otherpass",
        display_name="Other Member",
    )


@pytest.fixture
def other_headers(other_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(other_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


# ---------------------------------------------------------------------------
# TestGetEvent
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetEvent:
    def test_get_event_authenticated(self, api_client, auth_headers, rsvp_event):
        response = api_client.get(f"/api/community/events/{rsvp_event.id}/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(rsvp_event.id)
        assert data["title"] == "RSVP Event"

    def test_get_event_unauthenticated(self, api_client, rsvp_event):
        response = api_client.get(f"/api/community/events/{rsvp_event.id}/")
        assert response.status_code == 200
        data = response.json()
        # Links hidden for unauthenticated
        assert data["whatsapp_link"] == ""
        assert data["rsvp_enabled"] is False

    def test_get_event_not_found(self, api_client, auth_headers):
        response = api_client.get(
            "/api/community/events/00000000-0000-0000-0000-000000000000/",
            **auth_headers,
        )
        assert response.status_code == 404
        assert_error_code(response, Code.Event.NOT_FOUND)


# ---------------------------------------------------------------------------
# TestRSVP
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRSVP:
    def test_rsvp_attending(self, api_client, auth_headers, rsvp_event):
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp"] == RSVPStatus.ATTENDING

    def test_rsvp_maybe(self, api_client, auth_headers, rsvp_event):
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.MAYBE},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp"] == RSVPStatus.MAYBE

    def test_rsvp_cant_go(self, api_client, auth_headers, rsvp_event):
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.CANT_GO},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp"] == RSVPStatus.CANT_GO

    def test_rsvp_invalid_status(self, api_client, auth_headers, rsvp_event):
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": "going"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400

    def test_rsvp_disabled_event(self, api_client, auth_headers, no_rsvp_event):
        response = api_client.post(
            f"/api/community/events/{no_rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.RSVPS_NOT_ENABLED)

    def test_rsvp_event_not_found(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/events/00000000-0000-0000-0000-000000000000/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 404

    def test_rsvp_requires_auth(self, api_client, rsvp_event):
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_rsvp_upsert_updates_existing(self, api_client, auth_headers, rsvp_event):
        api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.CANT_GO},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp"] == RSVPStatus.CANT_GO
        # Still only one RSVP record
        from users.models import User

        user = User.objects.get(phone_number="+12025550101")
        assert EventRSVP.objects.filter(event=rsvp_event, user=user).count() == 1

    def test_rsvp_delete_success(self, api_client, auth_headers, rsvp_event, test_user):
        EventRSVP.objects.create(event=rsvp_event, user=test_user, status=RSVPStatus.ATTENDING)
        response = api_client.delete(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            **auth_headers,
        )
        assert response.status_code == 204
        assert not EventRSVP.objects.filter(event=rsvp_event, user=test_user).exists()

    def test_rsvp_delete_not_found(self, api_client, auth_headers, rsvp_event):
        response = api_client.delete(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            **auth_headers,
        )
        assert response.status_code == 404
        assert_error_code(response, Code.Event.RSVP_NOT_FOUND)

    def test_rsvp_delete_requires_auth(self, api_client, rsvp_event):
        response = api_client.delete(f"/api/community/events/{rsvp_event.id}/rsvp/")
        assert response.status_code == 401

    def test_creator_sees_guest_phone_numbers(
        self, api_client, auth_headers, rsvp_event, other_user, other_headers
    ):
        # other_user RSVPs
        api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **other_headers,
        )
        # Creator fetches event
        response = api_client.get(
            f"/api/community/events/{rsvp_event.id}/",
            **auth_headers,
        )
        assert response.status_code == 200
        guests = response.json()["guests"]
        assert len(guests) == 1
        assert guests[0]["phone"] == other_user.phone_number

    def test_non_creator_cannot_see_guest_phones(
        self, api_client, auth_headers, rsvp_event, other_user, other_headers
    ):
        # creator RSVPs
        api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        # other_user (not creator) fetches event
        response = api_client.get(
            f"/api/community/events/{rsvp_event.id}/",
            **other_headers,
        )
        assert response.status_code == 200
        guests = response.json()["guests"]
        assert len(guests) == 1
        assert guests[0]["phone"] is None


# ---------------------------------------------------------------------------
# TestCreateEventWithCohosts
# ---------------------------------------------------------------------------


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
