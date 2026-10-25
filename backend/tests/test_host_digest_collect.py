from datetime import timedelta
from itertools import count

import pytest
from community._host_digest import (
    build_host_digest,
    capacity_line,
    digest_recipients,
    eligible_events,
)
from community.models import (
    DEFAULT_EVENT_DURATION,
    Event,
    EventComment,
    EventRSVP,
    EventStatus,
    EventType,
    RSVPStatus,
)
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from notifications._email_helpers import format_eastern_datetime
from users._helpers import visible_display_name
from users.models import User
from users.roles import Role

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


def _comment(event: Event, author: User, at, **extra) -> EventComment:
    comment = EventComment.objects.create(event=event, author=author, body="secret words", **extra)
    EventComment.objects.filter(pk=comment.pk).update(created_at=at)
    return comment


def _only_event(host: User, run_at):
    digest = build_host_digest(host, run_at)
    assert digest is not None
    assert len(digest.events) == 1
    return digest.events[0]


def test_groups_rsvps_by_current_status(run_at):
    host = _user("host")
    event = _event(host)
    rsvps = [
        ("removed", RSVPStatus.REMOVED),
        ("chris", RSVPStatus.CANT_GO),
        ("sam", RSVPStatus.ATTENDING),
        ("max", RSVPStatus.MAYBE),
        ("alex", RSVPStatus.ATTENDING),
        ("jo", RSVPStatus.WAITLISTED),
    ]
    for minutes_ago, (name, status) in zip(range(60, 0, -1), rsvps, strict=False):
        _rsvp(event, _user(name), status, run_at - timedelta(minutes=minutes_ago))

    assert _only_event(host, run_at).rsvp_groups == [
        ("going", ["sam", "alex"]),
        ("maybe", ["max"]),
        ("waitlisted", ["jo"]),
        ("can't go", ["chris"]),
        ("removed", ["removed"]),
    ]


def test_excludes_cohost_rsvps_and_comments(run_at):
    host_a, host_b, guest = _user("ana"), _user("bea"), _user("guest")
    event = _event(host_a)
    event.co_hosts.add(host_b)
    at = run_at - HOUR
    for person in (host_a, host_b, guest):
        _rsvp(event, person, RSVPStatus.ATTENDING, at)
        _comment(event, person, at)

    for host in (host_a, host_b):
        digest_event = _only_event(host, run_at)
        assert digest_event.rsvp_groups == [("going", ["guest"])]
        assert digest_event.new_comment_count == 1


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


def test_events_sorted_tbd_last_with_when_and_url(run_at, settings):
    settings.FRONTEND_BASE_URL = "https://pda.example.com"
    host, guest = _user("host"), _user("guest")
    same_start = run_at + timedelta(days=3)
    events = [
        _event(host, "tbd", start_datetime=run_at - 72 * HOUR, datetime_tbd=True),
        _event(host, "later", start_datetime=run_at + timedelta(days=5)),
        _event(host, "b tie", start_datetime=same_start),
        _event(host, "a tie", start_datetime=same_start),
        _event(host, "sooner", start_datetime=run_at + timedelta(days=1)),
    ]
    for event in events:
        _rsvp(event, guest, RSVPStatus.ATTENDING, run_at - HOUR)

    digest = build_host_digest(host, run_at)

    assert digest is not None
    assert [e.title for e in digest.events] == ["sooner", "a tie", "b tie", "later", "tbd"]
    sooner, tbd = events[4], events[0]
    assert sooner.start_datetime is not None
    assert digest.events[0].when == format_eastern_datetime(sooner.start_datetime)
    assert digest.events[0].url == f"https://pda.example.com/events/{sooner.slug}"
    assert digest.events[-1].when == "to be decided"
    assert digest.events[-1].url == f"https://pda.example.com/events/{tbd.slug}"


def test_cohost_of_another_event_counts_as_guest(run_at):
    host, other_host = _user("host"), _user("x")
    _event(other_host, "a")
    event_b = _event(host, "b")
    _rsvp(event_b, other_host, RSVPStatus.ATTENDING, run_at - HOUR)
    _comment(event_b, other_host, run_at - HOUR)

    digest_event = _only_event(host, run_at)
    assert digest_event.title == "b"
    assert digest_event.rsvp_groups == [("going", ["x"])]
    assert digest_event.new_comment_count == 1


def test_comments_count_excludes_deleted_includes_replies(run_at):
    host, guest = _user("host"), _user("guest")
    event = _event(host, location="secret spot")
    at = run_at - HOUR
    parent = _comment(event, guest, at)
    _comment(event, guest, at)
    _comment(event, guest, at, parent=parent)
    _comment(event, guest, at, deleted_at=at)

    digest = build_host_digest(host, run_at)

    assert digest is not None
    assert digest.events[0].new_comment_count == 3
    assert digest.events[0].rsvp_groups == []
    assert "secret" not in repr(digest.events)


def test_window_edges(run_at):
    last_sent = run_at - 6 * HOUR
    host, guest = _user("host", host_digest_last_sent_at=last_sent), _user("guest")
    event = _event(host)
    after_run = run_at + timedelta(seconds=1)
    _rsvp(event, _user("at last sent"), RSVPStatus.ATTENDING, last_sent)
    _rsvp(event, _user("at run"), RSVPStatus.ATTENDING, run_at)
    _rsvp(event, _user("after run"), RSVPStatus.ATTENDING, after_run)
    for at in (last_sent, run_at, after_run):
        _comment(event, guest, at)

    digest_event = _only_event(host, run_at)
    assert digest_event.rsvp_groups == [("going", ["at run"])]
    assert digest_event.new_comment_count == 1


def test_null_watermark_uses_24h(run_at):
    host, guest = _user("host"), _user("guest")
    event = _event(host)
    _rsvp(event, _user("recent"), RSVPStatus.ATTENDING, run_at - 23 * HOUR)
    _rsvp(event, _user("stale"), RSVPStatus.ATTENDING, run_at - 25 * HOUR)
    _rsvp(event, _user("never stamped"), RSVPStatus.ATTENDING, None)
    _comment(event, guest, run_at - 23 * HOUR)
    _comment(event, guest, run_at - 25 * HOUR)

    digest_event = _only_event(host, run_at)
    assert digest_event.rsvp_groups == [("going", ["recent"])]
    assert digest_event.new_comment_count == 1


def test_no_activity_returns_none(run_at):
    host, guest = _user("host"), _user("guest")
    event = _event(host, max_attendees=2)
    long_ago = run_at - timedelta(days=3)
    _rsvp(event, guest, RSVPStatus.ATTENDING, long_ago)
    _rsvp(event, _user("other"), RSVPStatus.ATTENDING, long_ago)
    _comment(event, guest, long_ago)

    assert build_host_digest(host, run_at) is None
    assert build_host_digest(_user("hosts nothing"), run_at) is None


@pytest.mark.parametrize("host_is_admin", [False, True])
def test_hidden_last_name_respected(run_at, host_is_admin):
    host = _user("host")
    if host_is_admin:
        host.roles.add(Role.objects.get(name="admin", is_default=True))
    guest = _user("jo", "privatesurname", hide_last_name=True)
    _rsvp(_event(host), guest, RSVPStatus.ATTENDING, run_at - HOUR)

    [(_, names)] = _only_event(host, run_at).rsvp_groups

    assert names == [visible_display_name(guest, host)]
    assert ("privatesurname" in names[0]) is host_is_admin


def _digest_query_count(host_pk, run_at) -> int:
    host = User.objects.get(pk=host_pk)
    with CaptureQueriesContext(connection) as ctx:
        assert build_host_digest(host, run_at) is not None
    return len(ctx)


def test_query_count_constant(run_at):
    host = _user("host")
    at = run_at - HOUR
    first = _event(host, "first")
    _rsvp(first, _user("solo"), RSVPStatus.ATTENDING, at)
    baseline = _digest_query_count(host.pk, run_at)

    guests = [_user(f"guest{i}", "last", hide_last_name=i % 2 == 0) for i in range(4)]
    statuses = list(RSVPStatus)
    events = [first, *(_event(host, f"extra {i}") for i in range(4))]
    for i, guest in enumerate(guests[:3]):
        _rsvp(first, guest, statuses[i], at)
    for event in events[1:]:
        for i, guest in enumerate(guests):
            _rsvp(event, guest, statuses[i % len(statuses)], at)
    for event in events:
        parent = _comment(event, guests[0], at)
        _comment(event, guests[1], at, parent=parent)
    assert EventRSVP.objects.filter(event__in=events).count() == 20
    assert EventComment.objects.filter(event__in=events).count() == 10

    assert _digest_query_count(host.pk, run_at) == baseline
