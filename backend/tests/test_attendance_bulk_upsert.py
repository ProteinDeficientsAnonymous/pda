from datetime import timedelta

import pytest
from community.models import AttendanceStatus, Event, EventRSVP, RSVPStatus
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from users.models import Role, User
from users.permissions import PermissionKey

from tests.test_attendance_mark import _auth

IMPORT_URL = "/api/community/events/attendance-import/commit/"
MARK_URL = "/api/community/events/attendance-mark/"
_seq = {"n": 0}


@pytest.fixture
def admin(db):
    user = User.objects.create_user(phone_number="+12025554000", password="x", first_name="A")
    perms = [PermissionKey.MANAGE_EVENTS, PermissionKey.MANAGE_USERS]
    user.roles.add(Role.objects.create(name="attendance_admin", permissions=perms))
    return user


def _event(admin) -> Event:
    start = timezone.now() - timedelta(days=3)
    return Event.objects.create(title="e", start_datetime=start, created_by=admin)


def _users(event: Event, count: int) -> list[User]:
    users = []
    for i in range(count):
        _seq["n"] += 1
        user = User.objects.create_user(
            phone_number=f"+1202555{_seq['n']:04d}", password="x", first_name="m"
        )
        if i % 2:
            EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.MAYBE)
        users.append(user)
    return users


def _row(user: User) -> dict:
    return {
        "row_index": 0,
        "raw_name": "m",
        "partiful_status": "Going",
        "checked_in": True,
        "user_id": str(user.id),
        "skip": False,
    }


def _post(api_client, admin, url: str, payload: dict):
    with CaptureQueriesContext(connection) as ctx:
        response = api_client.post(url, payload, content_type="application/json", **_auth(admin))
    assert response.status_code == 200, response.content
    return response.json(), len(ctx.captured_queries)


def _import(api_client, admin, count: int):
    event = _event(admin)
    rows = [_row(u) for u in _users(event, count)]
    return _post(api_client, admin, IMPORT_URL, {"event_id": str(event.id), "rows": rows})


def _mark(api_client, admin, count: int):
    event = _event(admin)
    ids = [str(u.id) for u in _users(event, count)]
    return _post(api_client, admin, MARK_URL, {"event_id": str(event.id), "user_ids": ids})


@pytest.mark.django_db
class TestAttendanceBulkUpsert:
    @pytest.mark.parametrize("call", [_import, _mark])
    def test_constant_queries(self, api_client, admin, call):
        _, small = call(api_client, admin, 2)
        body, large = call(api_client, admin, 6)
        assert large == small
        assert (body["created_count"], body["updated_count"]) == (3, 3)

    def test_mirrors_rsvp_save_side_effects(self, api_client, admin):
        event = _event(admin)
        waitlisted, same, new = _users(event, 3)
        stamp = timezone.now() - timedelta(days=1)
        EventRSVP.objects.create(
            event=event, user=waitlisted, status=RSVPStatus.WAITLISTED, waitlist_position=1
        )
        EventRSVP.objects.filter(event=event, user=waitlisted).update(status_changed_at=stamp)
        EventRSVP.objects.filter(event=event, user=same).update(
            status=RSVPStatus.ATTENDING, status_changed_at=stamp
        )
        rows = [_row(waitlisted), _row(same), _row(new), _row(new)]
        body, _ = _post(api_client, admin, IMPORT_URL, {"event_id": str(event.id), "rows": rows})

        assert (body["created_count"], body["updated_count"]) == (1, 3)
        rsvps = {r.user_id: r for r in EventRSVP.objects.filter(event=event)}
        assert rsvps[waitlisted.pk].waitlist_position is None
        assert rsvps[waitlisted.pk].status_changed_at > stamp
        assert rsvps[same.pk].status_changed_at == stamp
        assert rsvps[new.pk].status_changed_at is not None
        assert all(r.attendance == AttendanceStatus.ATTENDED for r in rsvps.values())
