import threading

import pytest
from community.models import Event, EventPoll, PollOption
from django import db
from django.test import Client
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso


def _make_user(i):
    return User.objects.create_user(
        phone_number=f"+1415555{9200 + i}",
        password="Testpass123!",
        first_name=f"Finalizer{i}",
        last_name="",
    )


def _jwt_headers(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db(transaction=True)
class TestPollFinalizeRace:
    def test_concurrent_finalize_only_one_succeeds(self, test_user):
        """N co-hosts finalize the same poll with different winning options at
        once; select_for_update() on the poll row must serialize them so
        exactly one finalize lands and the rest get ALREADY_FINALIZED (Issue 1297)."""
        event = Event.objects.create(
            title="Race Poll Event",
            datetime_tbd=True,
            rsvp_enabled=True,
            created_by=test_user,
        )
        poll = EventPoll.objects.create(event=event, created_by=test_user)
        options = [
            PollOption.objects.create(poll=poll, datetime=future_iso(days=100 + i), display_order=i)
            for i in range(8)
        ]

        cohosts = [_make_user(i) for i in range(len(options))]
        event.co_hosts.set(cohosts)
        results = [None] * len(options)

        def finalize(i):
            try:
                client = Client()
                resp = client.post(
                    f"/api/community/events/{event.id}/poll/finalize/",
                    {"winning_option_id": str(options[i].id)},
                    content_type="application/json",
                    **_jwt_headers(cohosts[i]),
                )
                results[i] = resp.status_code
            finally:
                db.connections.close_all()

        threads = [threading.Thread(target=finalize, args=(i,)) for i in range(len(options))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count(200) == 1, results
        assert results.count(400) == len(options) - 1, results

        poll.refresh_from_db()
        assert poll.winning_option_id in {opt.id for opt in options}
