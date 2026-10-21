"""Tests for a waitlisted member editing their own RSVP (Issue 1289)."""

import pytest
from community.models import Event, EventRSVP, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


def _user(n):
    return User.objects.create_user(
        phone_number=f"+1202555{9300 + n}", password="x", first_name=f"U{n}"
    )


def _rsvp(api_client, event, user, status="attending", has_plus_one=False):
    return api_client.post(
        f"/api/community/events/{event.id}/rsvp/",
        {"status": status, "has_plus_one": has_plus_one},
        content_type="application/json",
        **_auth(user),
    )


def _status(event, user):
    return EventRSVP.objects.get(event=event, user=user).status


@pytest.fixture
def event(db):
    return Event.objects.create(
        title="Capped",
        start_datetime=future_iso(days=14),
        rsvp_enabled=True,
        max_attendees=2,
        allow_plus_ones=True,
        created_by=_user(0),
    )


@pytest.fixture
def seated(event):
    users = [_user(1), _user(2)]
    for u in users:
        EventRSVP.objects.create(event=event, user=u, status=RSVPStatus.ATTENDING)
    return users


@pytest.fixture
def line(event, seated):
    """Head of the line has a +1; second in line is solo."""
    head, second = _user(3), _user(4)
    EventRSVP.objects.create(
        event=event, user=head, status=RSVPStatus.WAITLISTED, has_plus_one=True
    )
    EventRSVP.objects.create(event=event, user=second, status=RSVPStatus.WAITLISTED)
    return head, second


@pytest.mark.django_db
class TestWaitlistedEdit:
    def test_adding_plus_one_keeps_place_in_line(self, api_client, event, line):
        _, second = line
        response = _rsvp(api_client, event, second, has_plus_one=True)
        assert response.status_code == 200
        row = EventRSVP.objects.get(event=event, user=second)
        assert row.status == RSVPStatus.WAITLISTED
        assert row.has_plus_one is True

    def test_resave_cannot_skip_blocked_head(self, api_client, event, seated, line):
        head, second = line
        EventRSVP.objects.filter(event=event, user=seated[0]).delete()
        # One seat open: the head's party of two doesn't fit, the solo second would.
        response = _rsvp(api_client, event, second)
        assert response.status_code == 200
        assert _status(event, second) == RSVPStatus.WAITLISTED
        assert _status(event, head) == RSVPStatus.WAITLISTED

    def test_head_dropping_plus_one_is_promoted(self, api_client, event, seated, line):
        head, second = line
        EventRSVP.objects.filter(event=event, user=seated[0]).delete()
        response = _rsvp(api_client, event, head, has_plus_one=False)
        assert response.status_code == 200
        assert _status(event, head) == RSVPStatus.ATTENDING
        assert _status(event, second) == RSVPStatus.WAITLISTED

    def test_head_leaving_line_lets_next_in(self, api_client, event, seated, line):
        head, second = line
        EventRSVP.objects.filter(event=event, user=seated[0]).delete()
        response = _rsvp(api_client, event, head, status="maybe")
        assert response.status_code == 200
        assert _status(event, head) == RSVPStatus.MAYBE
        assert _status(event, second) == RSVPStatus.ATTENDING

    def test_uncapped_event_seats_waitlisted_resave(self, api_client, event, line):
        _, second = line
        event.max_attendees = None
        event.save()
        response = _rsvp(api_client, event, second, has_plus_one=True)
        assert response.status_code == 200
        assert _status(event, second) == RSVPStatus.ATTENDING

    def test_waitlisted_status_still_rejected_as_input(self, api_client, event, line):
        _, second = line
        response = _rsvp(api_client, event, second, status="waitlisted")
        assert response.status_code == 400
