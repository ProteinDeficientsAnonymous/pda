import json
from itertools import count

import pytest
from community._polls import MAX_POLL_OPTIONS
from community._validation import Code
from community.models import Event, EventPoll, PollAvailability, PollOption, PollVote
from django.db import connection
from django.test.utils import CaptureQueriesContext
from users.models import User
from users.roles import Role

from tests._asserts import assert_error_code
from tests.conftest import future_iso

_phone_suffix = count(9000)


@pytest.fixture
def poll_event(db, test_user):
    return Event.objects.create(
        title="Poll Event",
        start_datetime=future_iso(days=90),
        created_by=test_user,
    )


def _make_poll(event, creator, option_count: int, voter_count: int) -> EventPoll:
    poll = EventPoll.objects.create(event=event, created_by=creator)
    voters = [
        User.objects.create_user(
            phone_number=f"+1202555{next(_phone_suffix):04d}",
            password="pass",
            first_name=f"Voter{i}",
            last_name=f"Hidden{i}",
            hide_last_name=True,
        )
        for i in range(voter_count)
    ]
    for i in range(option_count):
        opt = PollOption.objects.create(
            poll=poll, datetime=future_iso(days=120 + i), display_order=i
        )
        for voter in voters:
            PollVote.objects.create(option=opt, user=voter, availability=PollAvailability.YES)
    return poll


def _create_poll(api_client, headers, event, option_count: int):
    return api_client.post(
        f"/api/community/events/{event.id}/poll/",
        data=json.dumps({"options": [future_iso(days=120 + i) for i in range(option_count)]}),
        content_type="application/json",
        **headers,
    )


@pytest.mark.django_db
class TestPollOptionCap:
    def test_create_at_max_options(self, api_client, auth_headers, poll_event):
        response = _create_poll(api_client, auth_headers, poll_event, MAX_POLL_OPTIONS)
        assert response.status_code == 201
        assert len(response.json()["options"]) == MAX_POLL_OPTIONS

    def test_create_over_max_options(self, api_client, auth_headers, poll_event):
        response = _create_poll(api_client, auth_headers, poll_event, MAX_POLL_OPTIONS + 1)
        assert response.status_code == 400
        entry = assert_error_code(response, Code.Poll.TOO_MANY_OPTIONS)
        assert entry["params"]["max"] == MAX_POLL_OPTIONS

    def test_add_option_past_max_rejected(self, api_client, auth_headers, poll_event):
        assert (
            _create_poll(api_client, auth_headers, poll_event, MAX_POLL_OPTIONS).status_code == 201
        )
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/options/",
            data=json.dumps({"datetime": future_iso(days=200)}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Poll.TOO_MANY_OPTIONS)
        assert PollOption.objects.filter(poll__event=poll_event).count() == MAX_POLL_OPTIONS


@pytest.mark.django_db
class TestGetPollQueryCount:
    def _query_counts(self, api_client, headers, test_user):
        counts = []
        for option_count, voter_count in ((2, 1), (MAX_POLL_OPTIONS, 5)):
            event = Event.objects.create(
                title="Poll Event", start_datetime=future_iso(days=90), created_by=test_user
            )
            _make_poll(event, test_user, option_count, voter_count)
            with CaptureQueriesContext(connection) as queries:
                response = api_client.get(f"/api/community/events/{event.id}/poll/", **headers)
            assert response.status_code == 200
            counts.append(len(queries))
        return counts, response.json()

    def test_anonymous_query_count_is_constant(self, api_client, test_user):
        (small, large), data = self._query_counts(api_client, {}, test_user)
        assert small == large
        assert all(opt["yes_count"] == 5 and opt["yes_voters"] == [] for opt in data["options"])

    def test_member_query_count_is_constant(self, api_client, auth_headers, test_user):
        (small, large), data = self._query_counts(api_client, auth_headers, test_user)
        assert small == large
        names = {v["name"] for opt in data["options"] for v in opt["yes_voters"]}
        assert names == {f"Voter{i}" for i in range(5)}

    def test_admin_query_count_is_constant(self, api_client, auth_headers, test_user):
        admin_role, _ = Role.objects.get_or_create(name="admin", defaults={"is_default": True})
        test_user.roles.add(admin_role)
        (small, large), data = self._query_counts(api_client, auth_headers, test_user)
        assert small == large
        names = {v["name"] for opt in data["options"] for v in opt["yes_voters"]}
        assert names == {f"Voter{i} Hidden{i}" for i in range(5)}
