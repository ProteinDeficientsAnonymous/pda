from datetime import UTC, datetime, timedelta

import pytest
from community._attendance_analytics import (
    compute_member_stats,
    is_pause_candidate,
    user_rsvps_for_attendance,
)
from community.models import (
    AttendanceStatus,
    Event,
    EventRSVP,
    EventStatus,
    EventType,
    RSVPStatus,
)
from django.utils import timezone
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.tools.members_read import _page
from users._member_search import MemberFilters, MemberSort
from users.models import User

from tests.test_mcp_members_find import _find, _ids, _new, _of, _set_up

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

_OFFICIAL, _CLUB, _COMMUNITY = EventType.OFFICIAL, EventType.CLUB, EventType.COMMUNITY


@pytest.fixture
def admin(manage_users_user):
    User.objects.filter(pk=manage_users_user.pk).update(
        date_joined=timezone.now() - timedelta(days=400), last_login=timezone.now()
    )
    return manage_users_user


def _event_at(start: datetime | None, event_type=_OFFICIAL, status=EventStatus.ACTIVE) -> Event:
    return Event.objects.create(
        title="e", start_datetime=start, event_type=event_type, status=status
    )


def _event(days_ago: float | None, event_type=_OFFICIAL, status=EventStatus.ACTIVE) -> Event:
    start = None if days_ago is None else timezone.now() - timedelta(days=days_ago)
    return _event_at(start, event_type, status)


def _went(user, *events, attendance=AttendanceStatus.ATTENDED, status=RSVPStatus.ATTENDING):
    for event in events:
        EventRSVP.objects.create(user=user, event=event, status=status, attendance=attendance)


def _attended(days_ago: float, joined_days_ago: float = 400) -> User:
    user = _set_up(joined_days_ago)
    _went(user, _event(days_ago))
    return user


def _rows(user, **arguments) -> list[dict]:
    seen, offset = [], 0
    while offset is not None:
        page = _find(user, limit=3, offset=offset, **arguments)
        seen += page["members"]
        offset = page["next_offset"]
    return seen


def _parse(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _varied_members() -> list[User]:
    recent_club, old_official = _event(20, _CLUB), _event(200)
    out_of_window, future = _event(400), _event(-10)
    community = _event(5, _COMMUNITY)
    cancelled, draft = _event(3, status=EventStatus.CANCELLED), _event(3, status=EventStatus.DRAFT)
    deleted, undated = _event(3, status=EventStatus.DELETED), _event(None)

    regular, lapsed, only_old, unmarked, only_excluded, future_only, cant_go = (
        _set_up(500) for _ in range(7)
    )
    _went(regular, recent_club, old_official, out_of_window, community, undated)
    _went(lapsed, old_official)
    _went(lapsed, recent_club, attendance=AttendanceStatus.DIDNT_GO)
    _went(only_old, out_of_window)
    _went(unmarked, recent_club, old_official, attendance=AttendanceStatus.UNKNOWN)
    _went(only_excluded, community, cancelled, draft, deleted, undated)
    _went(future_only, future)
    _went(cant_go, recent_club, status=RSVPStatus.CANT_GO)
    return [regular, lapsed, only_old, unmarked, only_excluded, future_only, cant_go]


def test_attendance_matches_the_analytics_screen(admin):
    members = [admin, *_varied_members()]
    rows = {row["id"]: row for row in _rows(admin)}
    for member in members:
        stats = compute_member_stats(user_rsvps_for_attendance(member))
        row = rows[str(member.id)]
        assert _parse(row["last_qualifying_at"]) == stats.last_qualifying_at
        assert row["qualifying_count_12mo"] == stats.qualifying_count_12mo
    pause_candidates = {
        str(m.id)
        for m in members
        if is_pause_candidate(compute_member_stats(user_rsvps_for_attendance(m)))
    }
    assert _ids(admin, inactive_for_days=365) == pause_candidates


def test_varied_members_get_the_expected_attendance(admin):
    regular, lapsed, only_old, unmarked, only_excluded, future_only, cant_go = _varied_members()
    rows = {row["id"]: row for row in _rows(admin)}
    counts = {m: rows[str(m.id)]["qualifying_count_12mo"] for m in (regular, lapsed, cant_go)}
    assert counts == {regular: 2, lapsed: 1, cant_go: 1}
    assert _ids(admin, never_attended=True) == _of(admin, unmarked, only_excluded)
    assert _ids(admin, inactive_for_days=365) == _of(admin, only_old, unmarked, only_excluded)
    assert _ids(admin, inactive_for_days=30) == _of(
        admin, lapsed, only_old, unmarked, only_excluded
    )
    assert str(future_only.id) in _ids(admin, never_attended=False)


def test_window_boundary_matches_the_analytics_screen(admin, monkeypatch):
    now = datetime(2026, 10, 24, 12, 0, 0, 123456, tzinfo=UTC)
    monkeypatch.setattr(timezone, "now", lambda: now)
    edge = now - timedelta(days=365)
    on_edge, just_before = _set_up(500), _set_up(500)
    _went(on_edge, _event_at(edge))
    _went(just_before, _event_at(edge - timedelta(microseconds=1)))
    rows = {row["id"]: row for row in _rows(admin)}
    inactive = _ids(admin, inactive_for_days=365)
    assert rows[str(on_edge.id)]["qualifying_count_12mo"] == 1
    assert rows[str(just_before.id)]["qualifying_count_12mo"] == 0
    assert inactive == _of(admin, just_before)
    for member in (on_edge, just_before):
        stats = compute_member_stats(user_rsvps_for_attendance(member), now)
        assert rows[str(member.id)]["qualifying_count_12mo"] == stats.qualifying_count_12mo
        assert is_pause_candidate(stats) == (str(member.id) in inactive)


def test_inactive_for_days_counts_never_attended(admin):
    never = _set_up(400)
    stale = _attended(100)
    _attended(10)
    assert _ids(admin, inactive_for_days=30) == _of(admin, never, stale)
    assert _ids(admin, inactive_for_days=30, never_attended=False) == _of(stale)
    assert _ids(admin, never_attended=True) == _of(admin, never)


def test_joined_recently_and_never_attended(admin):
    match = _new(20)
    _went(_new(20), _event(5, _CLUB))
    _new(90)
    community_only = _new(30)
    _went(community_only, _event(5, _COMMUNITY))
    expected = _of(match, community_only)
    assert _ids(admin, joined_within_days=60, never_attended=True) == expected
    assert _ids(admin, joined_within_days=60, inactive_for_days=60) == expected


def test_longest_inactive_sorts_by_time_since_last_activity(admin):
    shared = _event(50)
    three_years = _attended(1095, joined_days_ago=1200)
    long_ago = _attended(200)
    tied = [_set_up(400), _set_up(100), _set_up(100)]
    for member in tied:
        _went(member, shared)
    tied_never = _set_up(50)
    User.objects.filter(pk=tied_never.pk).update(date_joined=shared.start_datetime)
    just_joined = _set_up(2)
    recent = _attended(1)
    ties = sorted([*tied, tied_never], key=lambda u: u.pk)
    expected = [three_years, admin, long_ago, *ties, just_joined, recent]
    ordered = [row["id"] for row in _rows(admin, sort=MemberSort.LONGEST_INACTIVE)]
    assert ordered == [str(u.id) for u in expected]


def test_default_sort_is_still_newest_member(admin):
    old, new = _attended(1, joined_days_ago=300), _set_up(5)
    assert [row["id"] for row in _rows(admin)] == [str(u.id) for u in (new, old, admin)]


def test_longest_inactive_paging_is_stable_with_ties(admin):
    shared = _event(30)
    for _ in range(4):
        _went(_set_up(), shared)
    for _ in range(3):
        _set_up()
    User.objects.update(date_joined=timezone.now() - timedelta(days=1))
    first = _find(admin, sort=MemberSort.LONGEST_INACTIVE, limit=100)
    paged = _rows(admin, sort=MemberSort.LONGEST_INACTIVE)
    assert first["total"] == len(paged) == 8
    assert [row["id"] for row in paged] == [row["id"] for row in first["members"]]


def test_one_page_is_two_queries_with_attendance(admin, django_assert_num_queries):
    for days in (5, 50, 500):
        _attended(days)
    filters = MemberFilters(inactive_for_days=30, never_attended=False)
    with django_assert_num_queries(2):
        page = _page(filters, 1, 0, True, MemberSort.LONGEST_INACTIVE)
    assert page["total"] == 2
    assert page["members"][0]["qualifying_count_12mo"] == 0


@pytest.mark.parametrize(
    "arguments",
    [
        {"sort": "oldest"},
        {"filters": {"inactive_for_days": 0}},
        {"filters": {"inactive_for_days": 3651}},
    ],
)
def test_bad_attendance_arguments_are_rejected(admin, arguments):
    with pytest.raises(ToolError):
        _find(admin, **arguments)
