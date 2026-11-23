from datetime import timedelta

import pytest
from audit.models import AuditLogEntry
from community.models import AttendanceStatus, Event, RSVPStatus
from django.utils import timezone

from tests._events import make_rsvp
from tests._mcp_tool_helpers import run_tool, tool_error
from tests._users import make_user

TOOL = "set_event_attendance"
pytestmark = pytest.mark.django_db


@pytest.fixture
def host(db):
    return make_user(first_name="Host")


@pytest.fixture
def guest(db):
    return make_user(first_name="Robin")


@pytest.fixture
def event(host):
    start = timezone.now() + timedelta(minutes=30)
    return Event.objects.create(
        title="potluck", start_datetime=start, rsvp_enabled=True, created_by=host
    )


def _args(event, guest, attendance) -> dict:
    return {"event_id": str(event.pk), "member_id": str(guest.pk), "attendance": attendance}


def _call(user, event, guest, attendance, **extra) -> dict:
    return run_tool(user, TOOL, **_args(event, guest, attendance), **extra)


def _refused(user, event, guest, attendance, **extra) -> str:
    return tool_error(user, TOOL, **_args(event, guest, attendance), **extra)


def _confirmed(user, event, guest, attendance, **extra) -> dict:
    token = _call(user, event, guest, attendance, **extra)["confirm_token"]
    return _call(user, event, guest, attendance, confirm_token=token, **extra)


def test_preview_changes_nothing(host, event, guest):
    rsvp = make_rsvp(event, guest)

    preview = _call(host, event, guest, AttendanceStatus.ATTENDED)

    assert preview.pop("confirm_token")
    assert preview == {
        "event": "potluck",
        "member": "Robin",
        "for_plus_one": False,
        "was": AttendanceStatus.UNKNOWN,
        "attendance": AttendanceStatus.ATTENDED,
    }
    rsvp.refresh_from_db()
    assert rsvp.attendance == AttendanceStatus.UNKNOWN


def test_confirm_marks_attended_and_audits(host, event, guest):
    rsvp = make_rsvp(event, guest)

    result = _confirmed(host, event, guest, AttendanceStatus.ATTENDED)

    assert result["attendance"] == AttendanceStatus.ATTENDED
    rsvp.refresh_from_db()
    assert rsvp.attendance == AttendanceStatus.ATTENDED
    assert rsvp.checked_in_at is not None
    entry = AuditLogEntry.objects.get(action="attendance_marked", target_id=str(event.pk))
    assert entry.details["attendance"] == AttendanceStatus.ATTENDED
    assert entry.details["via"] == "mcp"


@pytest.mark.parametrize("for_plus_one", [False, True])
def test_clearing_to_unknown_clears_check_in(host, event, guest, for_plus_one):
    rsvp = make_rsvp(
        event,
        guest,
        has_plus_one=True,
        attendance=AttendanceStatus.DIDNT_GO,
        checked_in_at=timezone.now(),
        plus_one_attendance=AttendanceStatus.ATTENDED,
        plus_one_checked_in_at=timezone.now(),
    )

    result = _confirmed(host, event, guest, AttendanceStatus.UNKNOWN, for_plus_one=for_plus_one)

    assert result["for_plus_one"] is for_plus_one
    assert result["was"] == (
        AttendanceStatus.ATTENDED if for_plus_one else AttendanceStatus.DIDNT_GO
    )
    rsvp.refresh_from_db()
    member = (rsvp.attendance, rsvp.checked_in_at is None)
    plus_one = (rsvp.plus_one_attendance, rsvp.plus_one_checked_in_at is None)
    cleared, kept = (plus_one, member) if for_plus_one else (member, plus_one)
    assert cleared == (AttendanceStatus.UNKNOWN, True)
    assert kept[1] is False


def test_refuses_a_member_who_cant_edit_the_event(event, guest):
    rsvp = make_rsvp(event, guest)

    error = _refused(make_user(), event, guest, AttendanceStatus.ATTENDED)

    assert '"status": 403' in error
    assert '"action": "set_attendance"' in error
    rsvp.refresh_from_db()
    assert rsvp.attendance == AttendanceStatus.UNKNOWN


def test_didnt_go_requires_a_going_rsvp(host, event, guest):
    make_rsvp(event, guest, status=RSVPStatus.MAYBE)

    error = _refused(host, event, guest, AttendanceStatus.DIDNT_GO)

    assert "didnt_go_requires_going" in error.lower()


def test_token_bound_to_the_mark(host, event, guest):
    make_rsvp(event, guest)
    token = _call(host, event, guest, AttendanceStatus.ATTENDED)["confirm_token"]

    error = _refused(host, event, guest, AttendanceStatus.DIDNT_GO, confirm_token=token)

    assert "doesn't match" in error


@pytest.mark.parametrize(("self_mark", "shown"), [(False, "Robin"), (True, "Robin Oak")])
def test_preview_honors_hide_last_name(host, event, self_mark, shown):
    guest = make_user(first_name="Robin", last_name="Oak", hide_last_name=True)
    if self_mark:
        event.co_hosts.add(guest)
    make_rsvp(event, guest)

    viewer = guest if self_mark else host
    assert _call(viewer, event, guest, AttendanceStatus.ATTENDED)["member"] == shown


def test_refuses_a_member_without_an_rsvp(host, event, guest):
    error = _refused(host, event, guest, AttendanceStatus.ATTENDED)

    assert '"status": 404' in error
    assert "rsvp_not_found" in error.lower()
