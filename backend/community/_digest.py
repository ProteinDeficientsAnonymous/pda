from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime

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


def weekly_digest_recipients(users: QuerySet[User]) -> QuerySet[User]:
    return users.filter(HAS_EMAIL, weekly_digest_opt_out=False)


def monthly_digest_recipients(users: QuerySet[User], today: date) -> QuerySet[User]:
    # Skipping anyone already sent today makes a cron re-run on the 1st retry only failures.
    return users.filter(HAS_EMAIL, monthly_digest_opt_out=False).exclude(
        monthly_digest_sent_on=today
    )


def send_digest_to_all(
    send: SendDigest,
    sender: EmailSender,
    recipients: QuerySet[User],
    payload: dict,
    on_sent: Callable[[User], None] | None = None,
) -> tuple[int, int]:
    sent = failed = 0
    for user in recipients:
        result = send(sender=sender, to=user.email, display_name=user.first_name, **payload)
        if result.success:
            sent += 1
            if on_sent:
                on_sent(user)
        else:
            failed += 1
    return sent, failed


def veganniversary_groups(*, today, users) -> list[dict]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for user in users:
        if user.veganniversary_month != today.month:
            continue
        years = today.year - user.veganniversary_year
        if years < 1:
            continue
        grouped[years].append(
            {
                "name": user.first_name,
                "url": f"{settings.FRONTEND_BASE_URL}/members/{user.pk}",
            }
        )
    return [
        {"label": "1 year" if y == 1 else f"{y} years", "people": people}
        for y, people in sorted(grouped.items(), reverse=True)
    ]


def shoutout_members() -> QuerySet[User]:
    return (
        User.objects.active_members()
        .filter(
            veganniversary_month__isnull=False,
            veganniversary_year__isnull=False,
            veganniversary_shoutout_opt_in=True,
        )
        .exclude(first_name="")
        .order_by("first_name")
    )
