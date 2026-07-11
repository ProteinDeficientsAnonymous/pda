"""Tests for the attendance report endpoint and member-list last_attended."""

from datetime import timedelta

import pytest
from community.models import AttendanceStatus, Event, EventRSVP, EventStatus, RSVPStatus
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture
def members(db):
    from users.models import User

    return [
        User.objects.create_user(
            phone_number=f"+1202555190{i}",
            password="x",
            display_name=f"Member {i}",
        )
        for i in range(1, 4)
    ]


@pytest.fixture
def host_user(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+12025551800",
        password="x",
        display_name="Host",
    )


@pytest.fixture
def events_admin(db):
    from users.models import Role, User
    from users.permissions import PermissionKey

    admin = User.objects.create_user(
        phone_number="+12025551801",
        password="x",
        display_name="Events Admin",
    )
    role = Role.objects.create(name="events_admin", permissions=[PermissionKey.MANAGE_EVENTS])
    admin.roles.add(role)
    return admin


def _make_event(host_user, title, days_ago):
    start = timezone.now() - timedelta(days=days_ago)
    return Event.objects.create(
        title=title,
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        rsvp_enabled=True,
        created_by=host_user,
        status=EventStatus.ACTIVE,
    )


@pytest.mark.django_db
class TestAttendanceReportEndpoint:
    def test_admin_sees_events_with_marks(self, api_client, host_user, members, events_admin):
        marked = _make_event(host_user, "Marked Event", days_ago=2)
        EventRSVP.objects.create(
            event=marked,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        EventRSVP.objects.create(
            event=marked,
            user=members[1],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.NO_SHOW,
        )
        EventRSVP.objects.create(
            event=marked,
            user=members[2],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.UNKNOWN,
        )

        response = api_client.get("/api/community/events/attendance-report/", **_auth(events_admin))
        assert response.status_code == 200
        rows = response.json()["events"]
        assert len(rows) == 1
        row = rows[0]
        assert row["event_id"] == str(marked.id)
        assert row["attended_count"] == 1
        assert row["no_show_count"] == 1
        assert row["going_count"] == 3

    def test_excludes_events_without_marks(self, api_client, host_user, members, events_admin):
        unmarked = _make_event(host_user, "No Marks", days_ago=1)
        EventRSVP.objects.create(event=unmarked, user=members[0], status=RSVPStatus.ATTENDING)

        response = api_client.get("/api/community/events/attendance-report/", **_auth(events_admin))
        assert response.status_code == 200
        assert response.json()["events"] == []

    def test_excludes_deleted_events(self, api_client, host_user, members, events_admin):
        deleted = _make_event(host_user, "Deleted Event", days_ago=3)
        EventRSVP.objects.create(
            event=deleted,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        Event.objects.filter(pk=deleted.pk).update(status=EventStatus.DELETED)

        response = api_client.get("/api/community/events/attendance-report/", **_auth(events_admin))
        assert response.status_code == 200
        assert response.json()["events"] == []

    def test_excludes_cancelled_events(self, api_client, host_user, members, events_admin):
        cancelled = _make_event(host_user, "Cancelled Event", days_ago=3)
        EventRSVP.objects.create(
            event=cancelled,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        Event.objects.filter(pk=cancelled.pk).update(status=EventStatus.CANCELLED)

        response = api_client.get("/api/community/events/attendance-report/", **_auth(events_admin))
        assert response.status_code == 200
        assert response.json()["events"] == []

    def test_stranded_mark_after_rsvp_change_not_counted(
        self, api_client, host_user, members, events_admin
    ):
        event = _make_event(host_user, "Flipped Event", days_ago=2)
        # Marked attended while ATTENDING, then flipped to CANT_GO — attendance
        # is not cleared, but the report must not count it.
        EventRSVP.objects.create(
            event=event,
            user=members[0],
            status=RSVPStatus.CANT_GO,
            attendance=AttendanceStatus.ATTENDED,
        )

        response = api_client.get("/api/community/events/attendance-report/", **_auth(events_admin))
        assert response.json()["events"] == []

    def test_sorted_newest_first(self, api_client, host_user, members, events_admin):
        older = _make_event(host_user, "Older", days_ago=10)
        newer = _make_event(host_user, "Newer", days_ago=1)
        for ev in (older, newer):
            EventRSVP.objects.create(
                event=ev,
                user=members[0],
                status=RSVPStatus.ATTENDING,
                attendance=AttendanceStatus.ATTENDED,
            )

        response = api_client.get("/api/community/events/attendance-report/", **_auth(events_admin))
        ids = [r["event_id"] for r in response.json()["events"]]
        assert ids == [str(newer.id), str(older.id)]

    def test_non_admin_forbidden(self, api_client, host_user, members):
        marked = _make_event(host_user, "Marked Event", days_ago=2)
        EventRSVP.objects.create(
            event=marked,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        response = api_client.get("/api/community/events/attendance-report/", **_auth(members[0]))
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get("/api/community/events/attendance-report/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestLastAttendedOnMemberList:
    def test_last_attended_is_most_recent_attended_event(
        self, api_client, host_user, members, manage_users_headers
    ):
        older = _make_event(host_user, "Older", days_ago=20)
        newer = _make_event(host_user, "Newer", days_ago=5)
        EventRSVP.objects.create(
            event=older,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        EventRSVP.objects.create(
            event=newer,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )

        response = api_client.get("/api/auth/users/", **manage_users_headers)
        assert response.status_code == 200
        row = next(r for r in response.json() if r["id"] == str(members[0].pk))
        assert row["last_attended"] is not None
        # The newer event's start should win.
        assert row["last_attended"][:10] == newer.start_datetime.date().isoformat()

    def test_last_attended_null_without_attended_rsvp(
        self, api_client, host_user, members, manage_users_headers
    ):
        event = _make_event(host_user, "No-show Event", days_ago=2)
        EventRSVP.objects.create(
            event=event,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.NO_SHOW,
        )

        response = api_client.get("/api/auth/users/", **manage_users_headers)
        row = next(r for r in response.json() if r["id"] == str(members[0].pk))
        assert row["last_attended"] is None

    def test_last_attended_excludes_stranded_mark_after_rsvp_change(
        self, api_client, host_user, members, manage_users_headers
    ):
        event = _make_event(host_user, "Flipped Event", days_ago=2)
        EventRSVP.objects.create(
            event=event,
            user=members[0],
            status=RSVPStatus.CANT_GO,
            attendance=AttendanceStatus.ATTENDED,
        )

        response = api_client.get("/api/auth/users/", **manage_users_headers)
        row = next(r for r in response.json() if r["id"] == str(members[0].pk))
        assert row["last_attended"] is None

    def test_last_attended_excludes_deleted_events(
        self, api_client, host_user, members, manage_users_headers
    ):
        deleted = _make_event(host_user, "Deleted Event", days_ago=2)
        EventRSVP.objects.create(
            event=deleted,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        Event.objects.filter(pk=deleted.pk).update(status=EventStatus.DELETED)

        response = api_client.get("/api/auth/users/", **manage_users_headers)
        row = next(r for r in response.json() if r["id"] == str(members[0].pk))
        assert row["last_attended"] is None

    def test_last_attended_excludes_cancelled_events(
        self, api_client, host_user, members, manage_users_headers
    ):
        cancelled = _make_event(host_user, "Cancelled Event", days_ago=2)
        EventRSVP.objects.create(
            event=cancelled,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        Event.objects.filter(pk=cancelled.pk).update(status=EventStatus.CANCELLED)

        response = api_client.get("/api/auth/users/", **manage_users_headers)
        row = next(r for r in response.json() if r["id"] == str(members[0].pk))
        assert row["last_attended"] is None
