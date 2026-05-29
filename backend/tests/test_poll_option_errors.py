"""Tests for poll-option create/update error narrowing (IntegrityError vs others)."""

import json
from unittest.mock import patch

import pytest
from community._validation import Code
from community.models import Event, EventPoll, PollOption

from tests._asserts import assert_error_code
from tests.conftest import future_iso


@pytest.fixture
def poll_event(db, test_user):
    return Event.objects.create(
        title="Poll Event",
        start_datetime=future_iso(days=90),
        created_by=test_user,
    )


@pytest.fixture
def poll_with_options(db, poll_event, test_user):
    poll = EventPoll.objects.create(event=poll_event, created_by=test_user)
    PollOption.objects.create(poll=poll, datetime=future_iso(days=120), display_order=0)
    PollOption.objects.create(poll=poll, datetime=future_iso(days=121), display_order=1)
    return poll


@pytest.mark.django_db
class TestAddPollOptionErrors:
    def test_duplicate_datetime_raises_already_exists(
        self, api_client, auth_headers, poll_event, poll_with_options
    ):
        existing = poll_with_options.options.first()
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/options/",
            data=json.dumps({"datetime": existing.datetime.isoformat()}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Poll.OPTION_ALREADY_EXISTS)

    def test_non_integrity_error_propagates(
        self, api_client, auth_headers, poll_event, poll_with_options
    ):
        # A non-IntegrityError from the DB layer must NOT be reported as a
        # duplicate — it should surface as a 500, not a misleading 400.
        with patch(
            "community._polls.PollOption.objects.create",
            side_effect=RuntimeError("db exploded"),
        ):
            with pytest.raises(RuntimeError, match="db exploded"):
                api_client.post(
                    f"/api/community/events/{poll_event.id}/poll/options/",
                    data=json.dumps({"datetime": future_iso(days=200)}),
                    content_type="application/json",
                    **auth_headers,
                )


@pytest.mark.django_db
class TestUpdatePollOptionErrors:
    def test_duplicate_datetime_raises_already_exists(
        self, api_client, auth_headers, poll_event, poll_with_options
    ):
        options = list(poll_with_options.options.all())
        first, second = options[0], options[1]
        # Move `second` onto `first`'s datetime → unique constraint violation.
        response = api_client.patch(
            f"/api/community/events/{poll_event.id}/poll/options/{second.id}/",
            data=json.dumps({"datetime": first.datetime.isoformat()}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Poll.OPTION_ALREADY_EXISTS)

    def test_non_integrity_error_propagates(
        self, api_client, auth_headers, poll_event, poll_with_options
    ):
        option = poll_with_options.options.first()
        with patch(
            "community._polls.PollOption.save",
            side_effect=RuntimeError("db exploded"),
        ):
            with pytest.raises(RuntimeError, match="db exploded"):
                api_client.patch(
                    f"/api/community/events/{poll_event.id}/poll/options/{option.id}/",
                    data=json.dumps({"datetime": future_iso(days=300)}),
                    content_type="application/json",
                    **auth_headers,
                )
