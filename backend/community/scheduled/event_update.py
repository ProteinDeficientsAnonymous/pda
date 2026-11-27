from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.conf import settings

from community.models import Club, Event, EventStatus, EventType, PageVisibility

WINDOW = timedelta(weeks=5)

FUNDING_NOTE = (
    "Note: money shouldn't be a barrier to come hang out with us! We have a small fund to "
    "assist folks that have financial barriers to attend our official events! Please reach out "
    "to me - it will be kept confidential!💞🌱"
)
SIGN_OFF = (
    "You're also welcome and invited to plan side quests in Side Quests & Hangouts! And we "
    "invite you to add them to the PDA calendar so people can easily find them!\n"
    "{calendar_url}\n\n"
    "We'll also be continuously improving the pda website so please leave feedback using the "
    "🐛 button!"
)


@dataclass(frozen=True)
class EventUpdate:
    text: str
    clubs_without_events: list[str]


def is_event_update_day(today: date) -> bool:
    """The 14th and the last day of the month."""
    return today.day == 14 or (today + timedelta(days=1)).day == 1


def _entry(event: Event) -> str:
    day = event.start_datetime.astimezone(settings.COMMUNITY_TZ)
    url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/events/{event.slug or event.pk}"
    return f"{day.month}/{day.day} {event.title}\n{url}"


def _club_entry(event: Event) -> str:
    # A deleted club leaves its events as club events with no club; list them without a name.
    return f"{event.club.name}\n{_entry(event)}" if event.club else _entry(event)


def _upcoming(now: datetime) -> list[Event]:
    return list(
        Event.objects.filter(
            status=EventStatus.ACTIVE,
            event_type__in=(EventType.OFFICIAL, EventType.CLUB),
            datetime_tbd=False,
            start_datetime__gte=now,
            start_datetime__lt=now + WINDOW,
        )
        .exclude(visibility=PageVisibility.INVITE_ONLY)
        .select_related("club")
        .order_by("start_datetime", "id")
    )


def build_event_update(now: datetime) -> EventUpdate:
    events = _upcoming(now)
    official = [_entry(e) for e in events if e.event_type == EventType.OFFICIAL]
    clubs = [_club_entry(e) for e in events if e.event_type == EventType.CLUB]
    sections = ["EVENT UPDATE"]
    if official:
        sections += ["Official PDA events:", *official, FUNDING_NOTE]
    if clubs:
        sections += ["CLUBS!", *clubs]
    sections.append(SIGN_OFF.format(calendar_url=f"{settings.FRONTEND_BASE_URL}/calendar"))
    with_events = {e.club_id for e in events}
    idle = Club.objects.exclude(id__in=with_events).order_by("name").values_list("name", flat=True)
    return EventUpdate(text="\n\n".join(sections), clubs_without_events=list(idle))
