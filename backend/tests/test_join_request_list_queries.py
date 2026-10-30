from datetime import timedelta

import pytest
from community.models import (
    Event,
    EventRSVP,
    EventType,
    JoinRequest,
    JoinRequestStatus,
    RSVPStatus,
)
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from users.models import User

URL = "/api/community/join-requests/"


def _seed_applicants(start: int, count: int) -> None:
    event = Event.objects.create(
        title="Potluck",
        event_type=EventType.OFFICIAL,
        start_datetime=timezone.now() + timedelta(days=3),
    )
    for i in range(start, start + count):
        phone = f"+1202555{i:04d}"
        user = User.objects.create(phone_number=phone, first_name="Sprout", is_member=False)
        EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.ATTENDING)
        JoinRequest.objects.create(
            first_name="Sprout", phone_number=phone, status=JoinRequestStatus.REJECTED
        )
        JoinRequest.objects.create(first_name="Sprout", phone_number=phone)


def _seed_linked_applicants(start: int, count: int) -> list[User]:
    """Requests linked via jr.user whose phone matches no user, so only that prefetch applies."""
    event = Event.objects.create(
        title="Picnic",
        event_type=EventType.OFFICIAL,
        start_datetime=timezone.now() + timedelta(days=3),
    )
    users = []
    for i in range(start, start + count):
        user = User.objects.create(phone_number=f"+1202555{i:04d}", first_name="Linked")
        EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.ATTENDING)
        JoinRequest.objects.create(first_name="Linked", phone_number=f"+1202666{i:04d}", user=user)
        users.append(user)
    return users


def _list_query_count(api_client, headers) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = api_client.get(URL, **headers)
    assert response.status_code == 200
    return len(ctx.captured_queries)


@pytest.mark.django_db
class TestJoinRequestListQueries:
    def test_query_count_does_not_grow_with_rows(self, api_client, vettor_headers):
        _seed_applicants(start=7000, count=2)
        _seed_linked_applicants(start=7050, count=2)
        small = _list_query_count(api_client, vettor_headers)
        _seed_applicants(start=7100, count=6)
        _seed_linked_applicants(start=7150, count=6)
        large = _list_query_count(api_client, vettor_headers)
        assert large == small

    def test_phone_matched_user_and_rejection_flags(self, api_client, vettor_headers):
        _seed_applicants(start=7200, count=1)
        listing = api_client.get(URL, **vettor_headers).json()
        by_status = {r["status"]: r for r in listing}
        fresh = by_status[JoinRequestStatus.PENDING]
        assert fresh["previously_rejected"] is True
        assert fresh["upcoming_official_count"] == 1
        assert fresh["user_id"] is not None
        assert by_status[JoinRequestStatus.REJECTED]["previously_rejected"] is False

    def test_linked_user_rows(self, api_client, vettor_headers):
        [user] = _seed_linked_applicants(start=7300, count=1)
        [row] = api_client.get(URL, **vettor_headers).json()
        assert row["user_id"] == str(user.id)
        assert row["upcoming_official_count"] == 1
        assert len(row["rsvp_events"]) == 1
