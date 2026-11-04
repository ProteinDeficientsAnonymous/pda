from datetime import timedelta

import pytest
from community.events.helpers import _can_edit_event
from community.models import Event, EventRSVP, RSVPStatus
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from users.models import User
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._users import make_user


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
    target = make_user()
    EventRSVP.objects.create(event=event, user=target, status=RSVPStatus.ATTENDING)
    for _ in range(guests):
        EventRSVP.objects.create(event=event, user=make_user(), status=RSVPStatus.ATTENDING)
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
    host = make_user()
    headers = auth_headers_for(host)
    counts = []
    for guests in (2, 6):
        event, target = _started_event(host, guests)
        path = f"/api/community/events/{event.id}/rsvps/{target.pk}/{suffix}"
        counts.append(_count(api_client, method, path, body, headers))
    assert counts[0] == counts[1]
    assert counts[0] <= ceiling


def _prefetched(event: Event) -> Event:
    return Event.objects.prefetch_related("co_hosts").get(pk=event.pk)


@pytest.mark.django_db
def test_can_edit_event_uses_prefetched_co_hosts(django_assert_num_queries):
    host = make_user()
    event = _prefetched(_started_event(host, 0)[0])
    viewer = User.objects.get(pk=host.pk)
    with django_assert_num_queries(0):
        assert _can_edit_event(viewer, event)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("permissions", "allowed"), [((), False), ((PermissionKey.MANAGE_EVENTS,), True)]
)
def test_can_edit_event_prefetched_non_host(permissions, allowed):
    event = _prefetched(_started_event(make_user(), 0)[0])
    assert _can_edit_event(make_user(*permissions), event) is allowed
