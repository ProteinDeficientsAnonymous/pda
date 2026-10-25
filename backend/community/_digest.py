from collections.abc import Callable
from datetime import datetime

from django.conf import settings
from django.db.models import QuerySet
from notifications._email_helpers import format_eastern_datetime
from notifications.email_sender import EmailSender, SendResult
from users.models import HAS_EMAIL, User

from community.models import Event, EventStatus, EventType

SendDigest = Callable[..., SendResult]


def _format_event_when(event: Event) -> str:
    if event.datetime_tbd or event.start_datetime is None:
        return "to be decided"
    return format_eastern_datetime(event.start_datetime)


def digest_events(*, start: datetime, end: datetime) -> list[dict]:
    upcoming = Event.objects.filter(
        status=EventStatus.ACTIVE,
        event_type__in=(EventType.OFFICIAL, EventType.CLUB),
        deleted_at__isnull=True,
        start_datetime__gte=start,
        start_datetime__lt=end,
    ).order_by("start_datetime")
    return [
        {
            "title": event.title,
            "when": _format_event_when(event),
            "url": f"{settings.FRONTEND_BASE_URL}/events/{event.slug or event.pk}",
        }
        for event in upcoming
    ]


def digest_urls() -> dict[str, str]:
    return {
        "calendar_url": f"{settings.FRONTEND_BASE_URL}/calendar",
        "settings_url": f"{settings.FRONTEND_BASE_URL}/settings",
    }


def digest_recipients(users: QuerySet[User]) -> QuerySet[User]:
    return users.filter(HAS_EMAIL, weekly_digest_opt_out=False)


def send_digest_to_all(
    send: SendDigest, sender: EmailSender, recipients, payload: dict
) -> tuple[int, int]:
    sent = failed = 0
    for user in recipients:
        result = send(sender=sender, to=user.email, display_name=user.first_name, **payload)
        if result.success:
            sent += 1
        else:
            failed += 1
    return sent, failed
