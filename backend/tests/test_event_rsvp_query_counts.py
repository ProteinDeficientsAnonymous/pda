import pytest
from community.models import Event, EventRSVP, RSVPStatus
from django.db import connection
from django.test.utils import CaptureQueriesContext
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso

_seq = {"n": 0}


def _user() -> User:
    _seq["n"] += 1
    return User.objects.create_user(
        phone_number=f"+1415666{_seq['n']:04d}", password="x", first_name=f"U{_seq['n']}"
    )


def _full_event(guests: int) -> Event:
    host = _user()
    event = Event.objects.create(
        title="Full",
        start_datetime=future_iso(days=5),
        created_by=host,
        rsvp_enabled=True,
        allow_plus_ones=True,
        max_attendees=guests,
    )
    event.co_hosts.add(host)
    for _ in range(guests):
        EventRSVP.objects.create(event=event, user=_user(), status=RSVPStatus.ATTENDING)
    return event


def _drop_plus_one(api_client, guests: int) -> int:
    """At capacity, dropping a +1 takes the over-capacity branch that needs the caller's row."""
    event = _full_event(guests)
    member = _user()
    EventRSVP.objects.create(
        event=event, user=member, status=RSVPStatus.ATTENDING, has_plus_one=True
    )
    headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(member).access_token}"}
    with CaptureQueriesContext(connection) as ctx:
        response = api_client.post(
            f"/api/community/events/{event.id}/rsvp/",
            {"status": "attending", "has_plus_one": False},
            content_type="application/json",
            **headers,
        )
    assert response.status_code == 200
    assert response.json()["my_rsvp"] == RSVPStatus.ATTENDING
    return len(ctx.captured_queries)


@pytest.mark.django_db
def test_member_rsvp_queries_are_bounded(api_client):
    small = _drop_plus_one(api_client, 2)
    large = _drop_plus_one(api_client, 6)
    assert small == large
    assert small <= 37
