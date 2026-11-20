import pytest
from community.models import EventRSVP, RSVPStatus
from django.db import connection
from django.test.utils import CaptureQueriesContext
from users.models import PublicRsvpToken, User

from tests._public_rsvp_helpers import make_official_event, make_public_rsvper
from tests._users import make_user


def _add_rsvped_events(public_rsvper: User, count: int) -> None:
    for _ in range(count):
        event = make_official_event()
        EventRSVP.objects.create(event=event, user=public_rsvper, status=RSVPStatus.ATTENDING)
        EventRSVP.objects.create(event=event, user=make_user(), status=RSVPStatus.ATTENDING)


def _count(api_client, token: str, expected_rsvps: int) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = api_client.get(f"/api/community/public/my-rsvps/?token={token}")
    assert response.status_code == 200
    assert len(response.json()["rsvps"]) == expected_rsvps
    return len(ctx.captured_queries)


@pytest.mark.django_db
def test_my_rsvps_prefetches_event_relations(api_client):
    public_rsvper = make_public_rsvper("+14155550001", "nm@example.com", name="non member")
    token = PublicRsvpToken.issue_or_extend(public_rsvper).token
    _add_rsvped_events(public_rsvper, 1)
    one = _count(api_client, token, 1)
    _add_rsvped_events(public_rsvper, 4)
    five = _count(api_client, token, 5)
    # _event_out still looks up the viewer's pending co-host invite per event.
    assert five - one <= 4
    assert one <= 16
