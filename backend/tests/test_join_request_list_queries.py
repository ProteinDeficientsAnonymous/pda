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


def _list_query_count(api_client, headers) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = api_client.get(URL, **headers)
    assert response.status_code == 200
    return len(ctx.captured_queries)


@pytest.mark.django_db
class TestJoinRequestListQueries:
    def test_query_count_does_not_grow_with_rows(self, api_client, vettor_headers):
        _seed_applicants(start=7000, count=2)
        small = _list_query_count(api_client, vettor_headers)
        _seed_applicants(start=7100, count=6)
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
