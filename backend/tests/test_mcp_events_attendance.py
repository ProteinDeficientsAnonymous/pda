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


def _call(user, event, guest, attendance, **extra) -> dict:
    args = {"event_id": str(event.pk), "member_id": str(guest.pk), "attendance": attendance}
    return run_tool(user, TOOL, **args, **extra)


def _confirmed(user, event, guest, attendance, **extra) -> dict:
    token = _call(user, event, guest, attendance, **extra)["confirm_token"]
    return _call(user, event, guest, attendance, confirm_token=token, **extra)


def test_preview_changes_nothing(host, event, guest):
    rsvp = make_rsvp(event, guest)

    preview = _call(host, event, guest, AttendanceStatus.ATTENDED)

    assert preview["was"] == AttendanceStatus.UNKNOWN
    assert preview["confirm_token"]
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
        status=RSVPStatus.MAYBE,
        has_plus_one=True,
        attendance=AttendanceStatus.ATTENDED,
        checked_in_at=timezone.now(),
        plus_one_attendance=AttendanceStatus.ATTENDED,
        plus_one_checked_in_at=timezone.now(),
    )

    result = _confirmed(host, event, guest, AttendanceStatus.UNKNOWN, for_plus_one=for_plus_one)

    assert result["was"] == AttendanceStatus.ATTENDED
    rsvp.refresh_from_db()
    cleared = (
        (rsvp.plus_one_attendance, rsvp.plus_one_checked_in_at)
        if for_plus_one
        else (rsvp.attendance, rsvp.checked_in_at)
    )
    kept = rsvp.checked_in_at if for_plus_one else rsvp.plus_one_checked_in_at
    assert cleared == (AttendanceStatus.UNKNOWN, None)
    assert kept is not None


def test_refuses_a_member_who_cant_edit_the_event(event, guest):
    rsvp = make_rsvp(event, guest)

    error = tool_error(
        make_user(),
        TOOL,
        event_id=str(event.pk),
        member_id=str(guest.pk),
        attendance=AttendanceStatus.ATTENDED,
    )

    assert '"status": 403' in error
    rsvp.refresh_from_db()
    assert rsvp.attendance == AttendanceStatus.UNKNOWN


def test_didnt_go_requires_a_going_rsvp(host, event, guest):
    make_rsvp(event, guest, status=RSVPStatus.MAYBE)

    error = tool_error(
        host,
        TOOL,
        event_id=str(event.pk),
        member_id=str(guest.pk),
        attendance=AttendanceStatus.DIDNT_GO,
    )

    assert "didnt_go_requires_going" in error.lower()


def test_token_bound_to_the_mark(host, event, guest):
    make_rsvp(event, guest)
    token = _call(host, event, guest, AttendanceStatus.ATTENDED)["confirm_token"]

    error = tool_error(
        host,
        TOOL,
        event_id=str(event.pk),
        member_id=str(guest.pk),
        attendance=AttendanceStatus.DIDNT_GO,
        confirm_token=token,
    )

    assert "doesn't match" in error


def test_preview_hides_a_hidden_last_name(host, event):
    guest = make_user(first_name="Robin", last_name="Oak", hide_last_name=True)
    make_rsvp(event, guest)

    assert _call(host, event, guest, AttendanceStatus.ATTENDED)["member"] == "Robin"
