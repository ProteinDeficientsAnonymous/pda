from datetime import datetime, timedelta

import pytest
from community.models import (
    AttendanceStatus,
    Event,
    EventRSVP,
    EventStatus,
    EventType,
    RSVPStatus,
    Survey,
)
from django.conf import settings
from users.models import User

TZ = settings.COMMUNITY_TZ
NOW = datetime(2026, 10, 15, 14, 0, tzinfo=TZ)
YESTERDAY_EVENING = datetime(2026, 10, 14, 20, 0, tzinfo=TZ)


@pytest.fixture
def feedback_survey(db):
    return Survey.objects.create(
        title="official feedback", slug="official-feedback", feedback_event_type=EventType.OFFICIAL
    )


def make_event(*, end=YESTERDAY_EVENING, event_type=EventType.OFFICIAL, **extra) -> Event:
    return Event.objects.create(
        title="Vegan Potluck",
        event_type=event_type,
        status=extra.pop("status", EventStatus.ACTIVE),
        start_datetime=end - timedelta(hours=2),
        end_datetime=end,
        **extra,
    )


_phone_counter = iter(range(1000, 9999))


def make_user(email: str | None = "auto") -> User:
    n = next(_phone_counter)
    return User.objects.create_user(
        phone_number=f"+1202555{n}",
        password="testpass123",
        first_name="Sam",
        email=f"u{n}@example.test" if email == "auto" else email,
    )


def make_rsvp(event: Event, user: User, attendance=AttendanceStatus.ATTENDED) -> EventRSVP:
    return EventRSVP.objects.create(
        event=event, user=user, status=RSVPStatus.ATTENDING, attendance=attendance
    )
