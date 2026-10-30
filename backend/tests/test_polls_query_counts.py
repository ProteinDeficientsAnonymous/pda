import json

import pytest
from community.models import EventPoll, PollAvailability, PollOption, PollVote
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests._events import make_event
from tests._time import future_iso


def _poll(creator, option_count: int) -> EventPoll:
    event = make_event(created_by=creator)
    poll = EventPoll.objects.create(event=event, created_by=creator)
    for i in range(option_count):
        PollOption.objects.create(poll=poll, datetime=future_iso(days=100 + i), display_order=i)
    return poll


def _post(api_client, url: str, payload: dict, headers: dict) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = api_client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
    assert response.status_code in (200, 201), response.content
    return len(ctx.captured_queries)


def _vote(api_client, poll: EventPoll, user, headers: dict) -> int:
    options = list(poll.options.all())
    for option in options[: len(options) // 2]:
        PollVote.objects.create(option=option, user=user, availability=PollAvailability.NO)
    votes = {str(o.id): PollAvailability.YES for o in options[:-1]}
    url = f"/api/community/events/{poll.event_id}/poll/vote/"
    return _post(api_client, url, {"votes": votes}, headers)


@pytest.mark.django_db
class TestPollQueryCounts:
    def test_vote_is_constant(self, api_client, auth_headers, test_user):
        small = _vote(api_client, _poll(test_user, 2), test_user, auth_headers)
        large_poll = _poll(test_user, 8)
        large = _vote(api_client, large_poll, test_user, auth_headers)
        assert large == small
        mine = PollVote.objects.filter(option__poll=large_poll, user=test_user)
        assert mine.count() == 7
        assert set(mine.values_list("availability", flat=True)) == {PollAvailability.YES}

    def test_revote_bumps_voted_at(self, api_client, auth_headers, test_user):
        poll = _poll(test_user, 2)
        option = poll.options.first()
        vote = PollVote.objects.create(option=option, user=test_user, availability="yes")
        url = f"/api/community/events/{poll.event_id}/poll/vote/"
        _post(api_client, url, {"votes": {str(option.id): "yes"}}, auth_headers)
        refreshed = PollVote.objects.get(pk=vote.pk)
        assert refreshed.voted_at > vote.voted_at

    def test_create_is_constant(self, api_client, auth_headers, test_user):
        def create(option_count: int) -> int:
            event = make_event(created_by=test_user)
            options = [future_iso(days=100 + i) for i in range(option_count)]
            url = f"/api/community/events/{event.id}/poll/"
            return _post(api_client, url, {"options": options}, auth_headers)

        assert create(2) == create(8)
