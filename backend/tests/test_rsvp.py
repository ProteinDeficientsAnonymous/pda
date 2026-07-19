"""Tests for event RSVP endpoints and event detail GET."""

from unittest.mock import patch

import pytest
from community._validation import Code
from community.models import Event, EventRSVP, EventStatus, PageVisibility, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User

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
        assert data["rsvp_enabled"] is True

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

    def test_rsvp_broadcasts_event_update_excluding_actor(
        self, api_client, auth_headers, rsvp_event, test_user
    ):
        with patch("community._event_rsvps.broadcast_capacity_change") as mock_broadcast:
            api_client.post(
                f"/api/community/events/{rsvp_event.id}/rsvp/",
                {"status": RSVPStatus.ATTENDING},
                content_type="application/json",
                **auth_headers,
            )
        mock_broadcast.assert_called_once()
        assert mock_broadcast.call_args.args[0] == rsvp_event.id
        assert mock_broadcast.call_args.kwargs["exclude_user_ids"] == {str(test_user.pk)}

    def test_delete_rsvp_fires_event_update_on_commit(
        self, api_client, auth_headers, rsvp_event, test_user, django_capture_on_commit_callbacks
    ):
        EventRSVP.objects.create(event=rsvp_event, user=test_user, status=RSVPStatus.ATTENDING)
        with (
            patch("community._event_helpers.broadcast_event_update") as mock_broadcast,
            django_capture_on_commit_callbacks(execute=True),
        ):
            api_client.delete(f"/api/community/events/{rsvp_event.id}/rsvp/", **auth_headers)
        mock_broadcast.assert_called_once()
        assert mock_broadcast.call_args.args[0].id == rsvp_event.id

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

    def test_resubmitting_same_status_does_not_bump_updated_at(
        self, api_client, auth_headers, rsvp_event, test_user
    ):
        api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        first_updated_at = EventRSVP.objects.get(event=rsvp_event, user=test_user).updated_at

        api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        second_updated_at = EventRSVP.objects.get(event=rsvp_event, user=test_user).updated_at

        assert second_updated_at == first_updated_at

    def test_rsvp_invalid_status(self, api_client, auth_headers, rsvp_event):
        # "going" is not an RSVPStatus member, so Pydantic rejects it at parse time (422).
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": "going"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422

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

    def test_rsvp_delete_broadcasts_capacity_change(
        self, api_client, auth_headers, rsvp_event, test_user
    ):
        EventRSVP.objects.create(event=rsvp_event, user=test_user, status=RSVPStatus.ATTENDING)
        with patch("community._event_rsvps.broadcast_capacity_change") as mock_broadcast:
            api_client.delete(f"/api/community/events/{rsvp_event.id}/rsvp/", **auth_headers)
        mock_broadcast.assert_called_once()
        assert mock_broadcast.call_args.args[0] == rsvp_event.id
        assert mock_broadcast.call_args.kwargs["exclude_user_ids"] == {str(test_user.pk)}

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

    def test_guest_list_flags_non_members(self, api_client, auth_headers, rsvp_event):
        non_member = User.objects.create_user(
            phone_number="+12025550199",
            password="testpass123",
            first_name="Guest",
            is_member=False,
        )
        EventRSVP.objects.create(event=rsvp_event, user=non_member, status=RSVPStatus.ATTENDING)
        response = api_client.get(f"/api/community/events/{rsvp_event.id}/", **auth_headers)
        assert response.status_code == 200
        guests = response.json()["guests"]
        assert len(guests) == 1
        assert guests[0]["is_member"] is False


# ---------------------------------------------------------------------------
# Draft / deleted RSVP gating (Issue 455)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRSVPDraftDeletedGating:
    def test_rsvp_blocked_on_draft_for_non_editor(self, api_client, other_headers, rsvp_event):
        # rsvp_event is owned by test_user; other_user can't edit it.
        rsvp_event.status = EventStatus.DRAFT
        rsvp_event.save(update_fields=["status"])
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 403
        assert not EventRSVP.objects.filter(event=rsvp_event).exists()

    def test_rsvp_allowed_on_draft_for_creator(self, api_client, auth_headers, rsvp_event):
        rsvp_event.status = EventStatus.DRAFT
        rsvp_event.save(update_fields=["status"])
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200

    def test_rsvp_blocked_on_deleted_event(self, api_client, auth_headers, rsvp_event):
        rsvp_event.status = EventStatus.DELETED
        rsvp_event.save(update_fields=["status"])
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 404

    def test_delete_rsvp_blocked_on_deleted_event(self, api_client, auth_headers, rsvp_event):
        EventRSVP.objects.create(
            event=rsvp_event, user=rsvp_event.created_by, status=RSVPStatus.ATTENDING
        )
        rsvp_event.status = EventStatus.DELETED
        rsvp_event.save(update_fields=["status"])
        response = api_client.delete(f"/api/community/events/{rsvp_event.id}/rsvp/", **auth_headers)
        assert response.status_code == 404


@pytest.mark.django_db
class TestDeleteRSVPWithdrawal:
    """An existing RSVP-holder can withdraw even after the event turned
    invite-only and excluded them (Issue 455 regression guard). The cancelled/
    past freezes are unaffected and covered by the existing RSVP suite."""

    def test_excluded_member_can_still_delete_stale_rsvp(
        self, api_client, other_headers, other_user, test_user, rsvp_event
    ):
        # other_user RSVPs ATTENDING while the event is public and full, with
        # test_user waitlisted behind them. The host then flips it to invite-only
        # without inviting other_user — they must still be able to withdraw, AND
        # withdrawing must free their spot so the waitlisted user is promoted.
        rsvp_event.max_attendees = 1
        rsvp_event.save(update_fields=["max_attendees"])
        EventRSVP.objects.create(event=rsvp_event, user=other_user, status=RSVPStatus.ATTENDING)
        waitlisted = EventRSVP.objects.create(
            event=rsvp_event, user=test_user, status=RSVPStatus.WAITLISTED
        )
        rsvp_event.visibility = PageVisibility.INVITE_ONLY
        rsvp_event.save(update_fields=["visibility"])

        response = api_client.delete(
            f"/api/community/events/{rsvp_event.id}/rsvp/", **other_headers
        )
        assert response.status_code == 204
        assert not EventRSVP.objects.filter(event=rsvp_event, user=other_user).exists()
        # Withdrawing an ATTENDING RSVP frees a spot → waitlist promotion fires.
        waitlisted.refresh_from_db()
        assert waitlisted.status == RSVPStatus.ATTENDING

    def test_non_rsvper_cannot_probe_invite_only_via_delete(
        self, api_client, other_headers, rsvp_event
    ):
        # A member with NO RSVP who can't see the invite-only event gets the
        # read-visibility 403 — they can't use delete to probe for existence.
        rsvp_event.visibility = PageVisibility.INVITE_ONLY
        rsvp_event.save(update_fields=["visibility"])

        response = api_client.delete(
            f"/api/community/events/{rsvp_event.id}/rsvp/", **other_headers
        )
        assert response.status_code == 403
