from datetime import datetime, timedelta

from community.models import (
    AttendanceStatus,
    Event,
    EventRSVP,
    EventStatus,
    EventType,
    RSVPStatus,
)
from django.conf import settings
from users.models import User

TZ = settings.COMMUNITY_TZ
NOW = datetime(2026, 10, 15, 14, 0, tzinfo=TZ)
YESTERDAY_EVENING = datetime(2026, 10, 14, 20, 0, tzinfo=TZ)


def make_ended_event(*, end=YESTERDAY_EVENING, event_type=EventType.OFFICIAL, **extra) -> Event:
    return Event.objects.create(
        title="Vegan Potluck",
        event_type=event_type,
        status=extra.pop("status", EventStatus.ACTIVE),
        start_datetime=end - timedelta(hours=2),
        end_datetime=end,
        **extra,
    )


def make_rsvp(event: Event, user: User, attendance=AttendanceStatus.ATTENDED) -> EventRSVP:
    return EventRSVP.objects.create(
        event=event, user=user, status=RSVPStatus.ATTENDING, attendance=attendance
    )
