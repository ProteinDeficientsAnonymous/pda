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
        phone_number=f"+1415333{_seq['n']:04d}", password="x", first_name=f"U{_seq['n']}"
    )


def _headers(user: User) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}


def _hosted_event(host: User, guests: int) -> Event:
    event = Event.objects.create(
        title="Busy", start_datetime=future_iso(days=5), created_by=host, rsvp_enabled=True
    )
    event.co_hosts.add(host)
    for _ in range(guests):
        EventRSVP.objects.create(event=event, user=_user(), status=RSVPStatus.ATTENDING)
        event.invited_users.add(_user())
    return event


def _patch(api_client, event: Event, headers: dict) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            {"title": "renamed"},
            content_type="application/json",
            **headers,
        )
    assert response.status_code == 200
    return len(ctx.captured_queries)


def _invite(api_client, event: Event, headers: dict) -> int:
    invitee = _user()
    with CaptureQueriesContext(connection) as ctx:
        response = api_client.post(
            f"/api/community/events/{event.id}/invitations/",
            {"user_ids": [str(invitee.pk)]},
            content_type="application/json",
            **headers,
        )
    assert response.status_code == 200
    return len(ctx.captured_queries)


@pytest.mark.django_db
@pytest.mark.parametrize(("send", "ceiling"), [(_patch, 26), (_invite, 26)])
def test_event_write_response_is_bounded(api_client, send, ceiling):
    host = _user()
    headers = _headers(host)
    small = send(api_client, _hosted_event(host, 2), headers)
    large = send(api_client, _hosted_event(host, 6), headers)
    assert large == small
    assert small <= ceiling
