import pytest
from community.models import Event, EventRSVP, RSVPStatus
from community.validation import Code
from django.utils import timezone

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._events import make_event, make_rsvp
from tests._public_rsvp_helpers import make_official_event, post
from tests._users import make_user


def _patch(api_client, event, user, body):
    return api_client.patch(
        f"/api/community/events/{event.id}/",
        body,
        content_type="application/json",
        **auth_headers_for(user),
    )


def _post_rsvp(api_client, event, user, status):
    return api_client.post(
        f"/api/community/events/{event.id}/rsvp/",
        {"status": status},
        content_type="application/json",
        **auth_headers_for(user),
    )


def _status(event, user) -> str:
    return EventRSVP.objects.get(event=event, user=user).status


@pytest.fixture
def guest(db):
    return make_user()


@pytest.fixture
def closed_event(test_user):
    return make_event(created_by=test_user, rsvp_enabled=True, rsvps_closed_at=timezone.now())


@pytest.fixture
def full_closed_event(closed_event, guest):
    """Cap 1: guest is going, another member waits in line."""
    closed_event.max_attendees = 1
    closed_event.save()
    waiter = make_user()
    make_rsvp(closed_event, guest, RSVPStatus.ATTENDING)
    make_rsvp(closed_event, waiter, RSVPStatus.WAITLISTED)
    return closed_event, waiter


@pytest.mark.django_db
class TestToggle:
    def test_close_sets_timestamp_and_out_flag(self, api_client, test_user):
        event = make_event(created_by=test_user, rsvp_enabled=True)
        response = _patch(api_client, event, test_user, {"rsvps_closed": True})
        assert response.status_code == 200
        assert response.json()["rsvps_closed"] is True
        event.refresh_from_db()
        assert event.rsvps_closed_at is not None

    def test_close_twice_keeps_first_timestamp(self, api_client, closed_event, test_user):
        first = closed_event.rsvps_closed_at
        assert (
            _patch(api_client, closed_event, test_user, {"rsvps_closed": True}).status_code == 200
        )
        closed_event.refresh_from_db()
        assert closed_event.rsvps_closed_at == first

    def test_reopen_clears_and_promotes_waitlist(
        self, api_client, full_closed_event, test_user, guest
    ):
        event, waiter = full_closed_event
        assert _post_rsvp(api_client, event, guest, RSVPStatus.CANT_GO).status_code == 200
        assert _status(event, waiter) == RSVPStatus.WAITLISTED

        response = _patch(api_client, event, test_user, {"rsvps_closed": False})
        assert response.status_code == 200
        assert response.json()["rsvps_closed"] is False
        assert _status(event, waiter) == RSVPStatus.ATTENDING

    def test_non_host_cannot_close(self, api_client, test_user, guest):
        event = make_event(created_by=test_user, rsvp_enabled=True)
        assert _patch(api_client, event, guest, {"rsvps_closed": True}).status_code == 403
        event.refresh_from_db()
        assert event.rsvps_closed_at is None


@pytest.mark.django_db
class TestGate:
    def test_new_rsvp_rejected(self, api_client, closed_event, guest):
        response = _post_rsvp(api_client, closed_event, guest, RSVPStatus.ATTENDING)
        assert response.status_code == 400
        assert_error_code(response, Code.Event.RSVPS_CLOSED_BY_HOST)
        assert not EventRSVP.objects.filter(event=closed_event, user=guest).exists()

    def test_public_rsvp_rejected(self, api_client):
        event = make_official_event(rsvps_closed_at=timezone.now())
        response = post(api_client, event)
        assert response.status_code == 400
        assert_error_code(response, Code.Event.RSVPS_CLOSED_BY_HOST)


@pytest.mark.django_db
class TestWaitlistFrozen:
    def test_cancel_does_not_promote(self, api_client, full_closed_event, guest):
        event, waiter = full_closed_event
        assert _post_rsvp(api_client, event, guest, RSVPStatus.CANT_GO).status_code == 200
        assert _status(event, waiter) == RSVPStatus.WAITLISTED

    def test_raising_cap_does_not_promote(self, api_client, full_closed_event, test_user):
        event, waiter = full_closed_event
        assert _patch(api_client, event, test_user, {"max_attendees": 5}).status_code == 200
        assert _status(event, waiter) == RSVPStatus.WAITLISTED
        assert Event.objects.get(pk=event.pk).rsvps_closed
