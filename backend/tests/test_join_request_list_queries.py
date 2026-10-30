from itertools import count

import pytest
from community.models import EventType, JoinRequest, JoinRequestStatus
from users.models import User

from tests._events import make_event, make_rsvp
from tests._query_counts import assert_constant_queries
from tests._users import make_user

URL = "/api/community/join-requests/"

_unmatched_phones = count(1)


def _seed_applicants(start: int, n: int) -> None:
    event = make_event(title="Potluck", event_type=EventType.OFFICIAL)
    for i in range(start, start + n):
        phone = f"+1202555{i:04d}"
        make_rsvp(event, make_user(phone_number=phone, first_name="Sprout", is_member=False))
        JoinRequest.objects.create(
            first_name="Sprout", phone_number=phone, status=JoinRequestStatus.REJECTED
        )
        JoinRequest.objects.create(first_name="Sprout", phone_number=phone)


def _seed_linked_applicants(n: int) -> list[User]:
    """Requests linked via jr.user whose phone matches no user, so only that prefetch applies."""
    event = make_event(title="Picnic", event_type=EventType.OFFICIAL)
    users = []
    for _ in range(n):
        user = make_user(first_name="Linked")
        make_rsvp(event, user)
        JoinRequest.objects.create(
            first_name="Linked", phone_number=f"+1202666{next(_unmatched_phones):04d}", user=user
        )
        users.append(user)
    return users


@pytest.mark.django_db
class TestJoinRequestListQueries:
    def test_query_count_does_not_grow_with_rows(self, api_client, vettor_headers):
        starts = count(7000, 100)

        def grow(n: int) -> None:
            _seed_applicants(next(starts), n)
            _seed_linked_applicants(n)

        assert_constant_queries(api_client, URL, grow, vettor_headers)

    def test_phone_matched_user_and_rejection_flags(self, api_client, vettor_headers):
        _seed_applicants(7900, 1)
        listing = api_client.get(URL, **vettor_headers).json()
        by_status = {r["status"]: r for r in listing}
        fresh = by_status[JoinRequestStatus.PENDING]
        assert fresh["previously_rejected"] is True
        assert fresh["upcoming_official_count"] == 1
        assert fresh["user_id"] is not None
        assert by_status[JoinRequestStatus.REJECTED]["previously_rejected"] is False

    def test_linked_user_rows(self, api_client, vettor_headers):
        [user] = _seed_linked_applicants(1)
        [row] = api_client.get(URL, **vettor_headers).json()
        assert row["user_id"] == str(user.id)
        assert row["upcoming_official_count"] == 1
        assert len(row["rsvp_events"]) == 1
