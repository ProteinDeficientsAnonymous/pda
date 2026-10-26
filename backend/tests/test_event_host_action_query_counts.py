from datetime import timedelta

import pytest
from community._event_helpers import _can_edit_event
from community.models import Event, EventRSVP, RSVPStatus
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User

_seq = {"n": 0}


def _user() -> User:
    _seq["n"] += 1
    return User.objects.create_user(
        phone_number=f"+1415222{_seq['n']:04d}", password="x", first_name=f"U{_seq['n']}"
    )


def _started_event(host: User, guests: int) -> tuple[Event, User]:
    event = Event.objects.create(
        title="Live",
        start_datetime=timezone.now() - timedelta(minutes=10),
        created_by=host,
        rsvp_enabled=True,
        price="$5",
        venmo_link="https://venmo.com/u/host",
    )
    event.co_hosts.add(host)
    target = _user()
    EventRSVP.objects.create(event=event, user=target, status=RSVPStatus.ATTENDING)
    for _ in range(guests):
        EventRSVP.objects.create(event=event, user=_user(), status=RSVPStatus.ATTENDING)
    return event, target


def _count(api_client, method: str, path: str, body: dict, headers: dict) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = getattr(api_client, method)(
            path, body, content_type="application/json", **headers
        )
    assert response.status_code == 200
    return len(ctx.captured_queries)


ACTIONS = [
    ("post", "attendance/", {"attendance": "attended"}, 26),
    ("post", "rsvp/", {"status": "maybe"}, 34),
    ("patch", "payment/", {"paid_confirmed": True}, 27),
]


@pytest.mark.django_db
@pytest.mark.parametrize(("method", "suffix", "body", "ceiling"), ACTIONS)
def test_host_action_queries_are_bounded(api_client, method, suffix, body, ceiling):
    host = _user()
    headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(host).access_token}"}
    counts = []
    for guests in (2, 6):
        event, target = _started_event(host, guests)
        path = f"/api/community/events/{event.id}/rsvps/{target.pk}/{suffix}"
        counts.append(_count(api_client, method, path, body, headers))
    assert counts[0] == counts[1]
    assert counts[0] <= ceiling


@pytest.mark.django_db
def test_can_edit_event_uses_prefetched_co_hosts(django_assert_num_queries):
    host = _user()
    event, _ = _started_event(host, 0)
    event = Event.objects.prefetch_related("co_hosts").get(pk=event.pk)
    viewer = User.objects.get(pk=host.pk)
    with django_assert_num_queries(0):
        assert _can_edit_event(viewer, event)
