"""Shared fixtures + helpers for the text-blast test files.

Lives in `_event_blasts_shared.py` (no `test_` prefix) so pytest doesn't try
to collect it as a test module. The send/list/detail tests live in
`test_event_blasts.py`; the inbound webhook tests live in
`test_event_blasts_webhook.py`. Both import from here.
"""

import json
from unittest.mock import patch

import pytest
from community.models import Event, EventCoHostInvite, EventRSVP, EventStatus, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso

TEST_TWILIO_TOKEN = "tok_test"
TEST_WEBHOOK_URL = "https://test.example/api/community/twilio/inbound/"


def make_user(phone: str, name: str = "Member") -> User:
    return User.objects.create_user(
        phone_number=phone,
        password="testpass123",
        display_name=name,
    )


def auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def make_event(creator: User) -> Event:
    return Event.objects.create(
        title="Community Potluck",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        status=EventStatus.ACTIVE,
        created_by=creator,
    )


def send_blast(api_client, sender: User, event: Event, **payload):
    return api_client.post(
        f"/api/community/events/{event.id}/text-blasts/",
        data=json.dumps(payload),
        content_type="application/json",
        **auth_headers(sender),
    )


@pytest.fixture
def creator(db) -> User:
    return make_user("+12025550401", "Creator")


@pytest.fixture
def cohost(db) -> User:
    return make_user("+12025550402", "Cohost")


@pytest.fixture
def attendee(db) -> User:
    return make_user("+12025550403", "Attendee")


@pytest.fixture
def maybe_attendee(db) -> User:
    return make_user("+12025550404", "MaybeAttendee")


@pytest.fixture
def stranger(db) -> User:
    return make_user("+12025550405", "Stranger")


@pytest.fixture
def event_with_attendees(creator, cohost, attendee, maybe_attendee) -> Event:
    """Active event with creator, accepted cohost, attending + maybe RSVPs."""
    event = make_event(creator)
    EventCoHostInvite.objects.create(
        event=event,
        user=cohost,
        invited_by=creator,
        status="accepted",
    )
    event.co_hosts.add(cohost)
    EventRSVP.objects.create(event=event, user=attendee, status=RSVPStatus.ATTENDING)
    EventRSVP.objects.create(event=event, user=maybe_attendee, status=RSVPStatus.MAYBE)
    return event


@pytest.fixture(autouse=True)
def _twilio_settings(settings):
    """Pretend Twilio is configured so signature paths work in tests."""
    settings.TWILIO_ACCOUNT_SID = "AC_test"
    settings.TWILIO_AUTH_TOKEN = TEST_TWILIO_TOKEN
    settings.TWILIO_FROM_NUMBER = "+15555550000"
    settings.TWILIO_INBOUND_WEBHOOK_URL = TEST_WEBHOOK_URL


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def mock_send_sms():
    """Patch send_sms to return a deterministic SID, no real Twilio calls."""
    with patch("community._sms.send_sms") as m:
        m.return_value = "SM_test_sid"
        yield m
