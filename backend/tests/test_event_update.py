from datetime import date, datetime, timedelta

import pytest
from community.models import Club, Event, EventStatus, EventType, PageVisibility
from community.scheduled.event_update import build_event_update, is_event_update_day
from django.conf import settings
from django.utils import timezone

pytestmark = pytest.mark.django_db

NOW = timezone.make_aware(datetime(2026, 11, 14, 12, 0))
BASE = settings.FRONTEND_BASE_URL.rstrip("/")


def _event(title, days, **fields):
    fields.setdefault("event_type", EventType.OFFICIAL)
    return Event.objects.create(title=title, start_datetime=NOW + timedelta(days=days), **fields)


def _club_event(title, days, club):
    return _event(title, days, event_type=EventType.CLUB, club=club)


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 11, 14), True),
        (date(2026, 11, 30), True),
        (date(2026, 12, 31), True),
        (date(2027, 2, 28), True),
        (date(2026, 11, 15), False),
        (date(2026, 11, 29), False),
    ],
)
def test_is_event_update_day(today, expected):
    assert is_event_update_day(today) is expected


def test_build_event_update_lists_official_then_clubs_by_date():
    movies, books = Club.objects.create(name="Movie Club"), Club.objects.create(name="Book Club")
    Club.objects.create(name="Doggie Meetup Club")
    party = _event("Holiday Party", 3)
    film = _club_event("Raise the Red Lantern", 1, movies)
    novel = _club_event("Homegoing", 5, books)
    update = build_event_update(NOW)
    assert update.text.startswith(
        "EVENT UPDATE\n\nOfficial PDA events:\n\n"
        f"11/17 Holiday Party\n{BASE}/events/{party.slug}\n\nNote: money"
    )
    assert (
        "CLUBS!\n\n"
        f"Movie Club\n11/15 Raise the Red Lantern\n{BASE}/events/{film.slug}\n\n"
        f"Book Club\n11/19 Homegoing\n{BASE}/events/{novel.slug}\n\n"
        "You're also welcome"
    ) in update.text
    assert update.text.endswith("using the ? button!")
    assert update.clubs_without_events == ["Doggie Meetup Club"]


def test_build_event_update_skips_hidden_and_out_of_window_events():
    _event("community picnic", 2, event_type=EventType.COMMUNITY)
    _event("secret", 2, visibility=PageVisibility.INVITE_ONLY)
    _event("draft", 2, status=EventStatus.DRAFT)
    _event("past", -1)
    _event("far", 40)
    update = build_event_update(NOW)
    assert update.text.startswith("EVENT UPDATE\n\nYou're also welcome")
