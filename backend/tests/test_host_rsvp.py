"""Tests for the host-driven guest RSVP endpoint (Issue 872)."""

from unittest.mock import patch

import pytest
from community.models import Event, EventRSVP, EventStatus, RSVPStatus
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import Role, User
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests.conftest import future_iso


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture
def host_user(db):
    return User.objects.create_user(phone_number="+12025559100", password="x", first_name="Host")


@pytest.fixture
def cohost_user(db):
    return User.objects.create_user(phone_number="+12025559101", password="x", first_name="Co-host")


@pytest.fixture
def admin_user(db):
    admin = User.objects.create_user(phone_number="+12025559102", password="x", first_name="Admin")
    role = Role.objects.create(name="rsvp_admin", permissions=[PermissionKey.MANAGE_EVENTS])
    admin.roles.add(role)
    return admin


@pytest.fixture
def guest(db):
    return User.objects.create_user(phone_number="+12025559103", password="x", first_name="Guest")


@pytest.fixture
def other_member(db):
    return User.objects.create_user(phone_number="+12025559104", password="x", first_name="Other")


@pytest.fixture
def host_rsvp_event(db, host_user, cohost_user):
    event = Event.objects.create(
        title="Host RSVP Event",
        start_datetime=future_iso(days=14),
        end_datetime=future_iso(days=14, hours=2),
        rsvp_enabled=True,
        created_by=host_user,
    )
    event.co_hosts.add(cohost_user)
    return event


@pytest.mark.django_db
class TestSetGuestRsvp:
    def test_host_changes_guest_rsvp(self, api_client, host_rsvp_event, host_user, guest):
        EventRSVP.objects.create(event=host_rsvp_event, user=guest, status=RSVPStatus.MAYBE)
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=host_rsvp_event, user=guest)
        assert rsvp.status == RSVPStatus.ATTENDING

    def test_host_creates_rsvp_for_guest_with_none(
        self, api_client, host_rsvp_event, host_user, guest
    ):
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 200
        assert EventRSVP.objects.filter(
            event=host_rsvp_event, user=guest, status=RSVPStatus.ATTENDING
        ).exists()

    def test_cohost_can_change_guest_rsvp(self, api_client, host_rsvp_event, cohost_user, guest):
        EventRSVP.objects.create(event=host_rsvp_event, user=guest, status=RSVPStatus.ATTENDING)
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.CANT_GO},
            content_type="application/json",
            **_auth(cohost_user),
        )
        assert response.status_code == 200

    def test_manage_events_admin_can_change_guest_rsvp(
        self, api_client, host_rsvp_event, admin_user, guest
    ):
        EventRSVP.objects.create(event=host_rsvp_event, user=guest, status=RSVPStatus.MAYBE)
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(admin_user),
        )
        assert response.status_code == 200

    def test_rejects_non_host(self, api_client, host_rsvp_event, other_member, guest):
        EventRSVP.objects.create(event=host_rsvp_event, user=guest, status=RSVPStatus.MAYBE)
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(other_member),
        )
        assert response.status_code == 403
        assert_error_code(response, "perm.denied")

    def test_rejects_unauthenticated(self, api_client, host_rsvp_event, guest):
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_event_not_found(self, api_client, host_user, guest):
        response = api_client.post(
            f"/api/community/events/00000000-0000-0000-0000-000000000000/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 404

    def test_target_user_not_found(self, api_client, host_rsvp_event, host_user):
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}"
            "/rsvps/00000000-0000-0000-0000-000000000000/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 404
        assert_error_code(response, "user.not_found")

    def test_rejects_waitlisted_as_input_status(
        self, api_client, host_rsvp_event, host_user, guest
    ):
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.WAITLISTED},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 400
        assert_error_code(response, "event.rsvp_invalid_status")

    def test_rejects_when_event_cancelled(self, api_client, host_rsvp_event, host_user, guest):
        host_rsvp_event.status = EventStatus.CANCELLED
        host_rsvp_event.save(update_fields=["status"])
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 400
        assert_error_code(response, "event.rsvps_closed_cancelled")

    def test_over_capacity_auto_waitlists(
        self, api_client, host_rsvp_event, host_user, guest, other_member
    ):
        host_rsvp_event.max_attendees = 1
        host_rsvp_event.save(update_fields=["max_attendees"])
        EventRSVP.objects.create(
            event=host_rsvp_event, user=other_member, status=RSVPStatus.ATTENDING
        )
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=host_rsvp_event, user=guest)
        assert rsvp.status == RSVPStatus.WAITLISTED

    def test_freeing_spot_promotes_waitlisted_guest(
        self, api_client, host_rsvp_event, host_user, guest, other_member
    ):
        host_rsvp_event.max_attendees = 1
        host_rsvp_event.save(update_fields=["max_attendees"])
        EventRSVP.objects.create(event=host_rsvp_event, user=guest, status=RSVPStatus.ATTENDING)
        waitlisted = EventRSVP.objects.create(
            event=host_rsvp_event, user=other_member, status=RSVPStatus.WAITLISTED
        )
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.CANT_GO},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 200
        waitlisted.refresh_from_db()
        assert waitlisted.status == RSVPStatus.ATTENDING

    def test_stamps_cancelled_at_on_transition_to_cant_go(
        self, api_client, host_rsvp_event, host_user, guest
    ):
        EventRSVP.objects.create(event=host_rsvp_event, user=guest, status=RSVPStatus.ATTENDING)
        before = timezone.now()
        response = api_client.post(
            f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
            {"status": RSVPStatus.CANT_GO},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=host_rsvp_event, user=guest)
        assert rsvp.cancelled_at is not None
        assert rsvp.cancelled_at >= before

    def test_broadcasts_capacity_change_excluding_actor(
        self, api_client, host_rsvp_event, host_user, guest
    ):
        with patch("community._event_host_actions.broadcast_capacity_change") as mock_broadcast:
            api_client.post(
                f"/api/community/events/{host_rsvp_event.id}/rsvps/{guest.pk}/rsvp/",
                {"status": RSVPStatus.ATTENDING},
                content_type="application/json",
                **_auth(host_user),
            )
        mock_broadcast.assert_called_once()
        assert mock_broadcast.call_args.args[0] == host_rsvp_event.id
        assert mock_broadcast.call_args.kwargs["exclude_user_ids"] == {str(host_user.pk)}
