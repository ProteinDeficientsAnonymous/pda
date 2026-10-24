"""Hosts can add and manage guests after an event ends; members can't self-rsvp (Issue 1588)."""

from datetime import timedelta

import pytest
from community.models import Event, EventRSVP, RSVPStatus
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import Role, User
from users.permissions import PermissionKey

from tests._asserts import assert_error_code


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


def _guest_rsvp_url(event, user):
    return f"/api/community/events/{event.id}/rsvps/{user.pk}/rsvp/"


@pytest.fixture
def host(db):
    return User.objects.create_user(phone_number="+12025559200", password="x", first_name="Host")


@pytest.fixture
def cohost(db):
    return User.objects.create_user(phone_number="+12025559201", password="x", first_name="Co")


@pytest.fixture
def manager(db):
    user = User.objects.create_user(phone_number="+12025559202", password="x", first_name="Mgr")
    user.roles.add(Role.objects.create(name="past_mgr", permissions=[PermissionKey.MANAGE_EVENTS]))
    return user


@pytest.fixture
def guest(db):
    return User.objects.create_user(
        phone_number="+12025559203", password="x", first_name="Guest", email="guest@e.com"
    )


@pytest.fixture
def other(db):
    return User.objects.create_user(phone_number="+12025559204", password="x", first_name="Other")


@pytest.fixture
def past_event(db, host, cohost):
    now = timezone.now()
    event = Event.objects.create(
        title="Past Potluck",
        start_datetime=now - timedelta(days=2),
        end_datetime=now - timedelta(days=2) + timedelta(hours=2),
        rsvp_enabled=True,
        created_by=host,
    )
    event.co_hosts.add(cohost)
    return event


@pytest.mark.django_db
class TestHostAddsGuestAfterEventEnds:
    @pytest.mark.parametrize("actor_fixture", ["host", "cohost", "manager"])
    def test_host_side_add_after_end_marks_going(
        self, request, api_client, past_event, guest, actor_fixture
    ):
        actor = request.getfixturevalue(actor_fixture)
        response = api_client.post(
            _guest_rsvp_url(past_event, guest),
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(actor),
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=past_event, user=guest)
        assert rsvp.status == RSVPStatus.ATTENDING

    def test_non_host_still_cannot_add_after_end(self, api_client, past_event, other, guest):
        response = api_client.post(
            _guest_rsvp_url(past_event, guest),
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(other),
        )
        assert response.status_code == 403
        assert_error_code(response, "perm.denied")

    def test_add_after_end_ignores_capacity(self, api_client, past_event, host, guest, other):
        past_event.max_attendees = 1
        past_event.save(update_fields=["max_attendees"])
        EventRSVP.objects.create(event=past_event, user=other, status=RSVPStatus.ATTENDING)
        response = api_client.post(
            _guest_rsvp_url(past_event, guest),
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(host),
        )
        assert response.status_code == 200
        assert EventRSVP.objects.get(event=past_event, user=guest).status == RSVPStatus.ATTENDING

    def test_add_after_end_sends_no_youre_in_email(
        self, api_client, past_event, host, guest, fake_email_sender
    ):
        response = api_client.post(
            _guest_rsvp_url(past_event, guest),
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(host),
        )
        assert response.status_code == 200
        fake_email_sender.send.assert_not_called()

    def test_removing_guest_after_end_does_not_promote_waitlist(
        self, api_client, past_event, host, guest, other
    ):
        past_event.max_attendees = 1
        past_event.save(update_fields=["max_attendees"])
        EventRSVP.objects.create(event=past_event, user=guest, status=RSVPStatus.ATTENDING)
        waitlisted = EventRSVP.objects.create(
            event=past_event, user=other, status=RSVPStatus.WAITLISTED
        )
        response = api_client.delete(_guest_rsvp_url(past_event, guest), **_auth(host))
        assert response.status_code == 204
        assert not EventRSVP.objects.filter(event=past_event, user=guest).exists()
        waitlisted.refresh_from_db()
        assert waitlisted.status == RSVPStatus.WAITLISTED


@pytest.mark.django_db
class TestMemberSelfRsvpAfterEventEnds:
    def test_member_cannot_self_rsvp_after_end(self, api_client, past_event, guest):
        response = api_client.post(
            f"/api/community/events/{past_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(guest),
        )
        assert response.status_code == 400
        assert_error_code(response, "event.rsvps_closed_past")
        assert not EventRSVP.objects.filter(event=past_event, user=guest).exists()

    def test_member_cannot_withdraw_after_end(self, api_client, past_event, guest):
        EventRSVP.objects.create(event=past_event, user=guest, status=RSVPStatus.ATTENDING)
        response = api_client.delete(f"/api/community/events/{past_event.id}/rsvp/", **_auth(guest))
        assert response.status_code == 400
        assert_error_code(response, "event.rsvps_closed_past")
