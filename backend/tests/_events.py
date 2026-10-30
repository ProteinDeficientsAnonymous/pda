from datetime import timedelta

from community.models import Event, EventRSVP, RSVPStatus
from django.utils import timezone


def make_event(**overrides) -> Event:
    fields = {"title": "Test Event", "start_datetime": timezone.now() + timedelta(days=30)}
    return Event.objects.create(**{**fields, **overrides})


def make_rsvp(event: Event, user, status: str = RSVPStatus.ATTENDING, **extra) -> EventRSVP:
    return EventRSVP.objects.create(event=event, user=user, status=status, **extra)
