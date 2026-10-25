from datetime import timedelta
from itertools import count

import pytest
from community._host_digest import capacity_line, digest_recipients, eligible_events
from community.models import (
    DEFAULT_EVENT_DURATION,
    Event,
    EventRSVP,
    EventStatus,
    EventType,
    RSVPStatus,
)
from django.utils import timezone
from users.models import User

pytestmark = pytest.mark.django_db

HOUR = timedelta(hours=1)
_phones = count(200)


@pytest.fixture
def run_at():
    return timezone.now()


def _user(first: str, last: str = "", **extra) -> User:
    phone = f"+1202555{next(_phones):04d}"
    extra.setdefault("email", f"{phone[1:]}@example.test")
    return User.objects.create_user(
        phone_number=phone, password="pw", first_name=first, last_name=last, **extra
    )


def _event(host: User, title: str = "hike", **extra) -> Event:
    extra.setdefault("start_datetime", timezone.now() + timedelta(days=3))
    extra.setdefault("rsvp_enabled", True)
    return Event.objects.create(title=title, created_by=host, **extra)


def _rsvp(event: Event, user: User, status: str, at, **extra) -> EventRSVP:
    rsvp = EventRSVP.objects.create(event=event, user=user, status=status, **extra)
    EventRSVP.objects.filter(pk=rsvp.pk).update(status_changed_at=at)
    return rsvp


def test_event_eligibility(run_at):
    host = _user("host")
    included = {
        "upcoming": {},
        "tbd": {"start_datetime": None, "datetime_tbd": True},
        "tbd with stale start": {"start_datetime": run_at - 72 * HOUR, "datetime_tbd": True},
        "ended 2h ago": {"start_datetime": run_at - 4 * HOUR, "end_datetime": run_at - 2 * HOUR},
        "in progress": {"start_datetime": run_at - 48 * HOUR, "end_datetime": run_at + HOUR},
        "no end, ran out 23h ago": {"start_datetime": run_at - 23 * HOUR - DEFAULT_EVENT_DURATION},
        "community": {"event_type": EventType.COMMUNITY},
        "club": {"event_type": EventType.CLUB},
        "official": {"event_type": EventType.OFFICIAL},
    }
    excluded = {
        "cancelled": {"status": EventStatus.CANCELLED},
        "draft": {"status": EventStatus.DRAFT},
        "deleted": {"status": EventStatus.DELETED, "deleted_at": run_at},
        "deleted_at only": {"deleted_at": run_at},
        "rsvp off": {"rsvp_enabled": False},
        "ended 25h ago": {"start_datetime": run_at - 27 * HOUR, "end_datetime": run_at - 25 * HOUR},
        "no end, ran out 25h ago": {"start_datetime": run_at - 25 * HOUR - DEFAULT_EVENT_DURATION},
    }
    for title, extra in {**included, **excluded}.items():
        _event(host, title, **extra)

    assert set(eligible_events(run_at).values_list("title", flat=True)) == set(included)


def test_capacity_line(run_at):
    host = _user("host")
    goers = [_user(f"goer{i}") for i in range(10)]
    waiters = [_user(f"waiter{i}") for i in range(3)]
    at = run_at - HOUR
    full = _event(host, "full", max_attendees=12)
    for i, goer in enumerate(goers):
        _rsvp(full, goer, RSVPStatus.ATTENDING, at, has_plus_one=i < 2)
    for waiter in waiters:
        _rsvp(full, waiter, RSVPStatus.WAITLISTED, at)
    capped, uncapped = _event(host, "capped", max_attendees=10), _event(host, "uncapped")
    uncapped_waitlist = _event(host, "uncapped waitlist")
    for event in (capped, uncapped, uncapped_waitlist):
        for goer in goers[:5]:
            _rsvp(event, goer, RSVPStatus.ATTENDING, at)
    for waiter in waiters[:2]:
        _rsvp(uncapped_waitlist, waiter, RSVPStatus.WAITLISTED, at)

    assert {e.title: capacity_line(e) for e in eligible_events(run_at)} == {
        "full": "12/12 going · full · 3 waitlisted",
        "capped": "5/10 going",
        "uncapped": "5 going",
        "uncapped waitlist": "5 going · 2 waitlisted",
    }


def test_recipients_filter(run_at):
    included = _user("host")
    _event(included, "first")
    eligible = _event(included, "second")
    eligible.co_hosts.add(
        _user("no email", email=None),
        _user("blank email", email=""),
        _user("opted out", host_digest_opt_out=True),
        _user("paused", is_paused=True),
        _user("archived", archived_at=run_at),
        _user("non member", is_member=False),
    )
    _event(_user("ineligible only"), "cancelled", status=EventStatus.CANCELLED)

    assert list(digest_recipients(run_at)) == [included]
