"""Tests for the attendance report endpoint and member-list last_attended."""

from datetime import timedelta

import pytest
from community.models import AttendanceStatus, Event, EventRSVP, EventStatus, EventType, RSVPStatus
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
            first_name=f"Member {i}",
            last_name="",
        )
        for i in range(1, 4)
    ]


@pytest.fixture
def host_user(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+12025551800",
        password="x",
        first_name="Host",
        last_name="",
    )


@pytest.fixture
def events_admin(db):
    from users.models import Role, User
    from users.permissions import PermissionKey

    admin = User.objects.create_user(
        phone_number="+12025551801",
        password="x",
        first_name="Events",
        last_name="Admin",
    )
    role = Role.objects.create(name="events_admin", permissions=[PermissionKey.MANAGE_EVENTS])
    admin.roles.add(role)
    return admin


def _make_event(host_user, title, days_ago, event_type=EventType.COMMUNITY):
    start = timezone.now() - timedelta(days=days_ago)
    return Event.objects.create(
        title=title,
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        rsvp_enabled=True,
        created_by=host_user,
        status=EventStatus.ACTIVE,
        event_type=event_type,
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
            attendance=AttendanceStatus.DIDNT_GO,
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

    def test_going_count_includes_plus_ones(self, api_client, host_user, members, events_admin):
        event = _make_event(host_user, "Plus One Event", days_ago=2)
        EventRSVP.objects.create(
            event=event,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
            has_plus_one=True,
        )
        EventRSVP.objects.create(
            event=event,
            user=members[1],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.UNKNOWN,
        )

        response = api_client.get("/api/community/events/attendance-report/", **_auth(events_admin))
        row = response.json()["events"][0]
        # 2 attending rsvps, one with a +1 → headcount 3, matching event detail.
        assert row["going_count"] == 3

    def test_excludes_draft_events(self, api_client, host_user, members, events_admin):
        draft = _make_event(host_user, "Draft Event", days_ago=3)
        EventRSVP.objects.create(
            event=draft,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        Event.objects.filter(pk=draft.pk).update(status=EventStatus.DRAFT)

        response = api_client.get("/api/community/events/attendance-report/", **_auth(events_admin))
        assert response.json()["events"] == []

    def test_attended_mark_counts_regardless_of_later_status_change(
        self, api_client, host_user, members, events_admin
    ):
        event = _make_event(host_user, "Flipped Event", days_ago=2)
        # Marked attended while ATTENDING, then flipped to CANT_GO — the mark
        # is a fact that happened, so the report must still count it.
        EventRSVP.objects.create(
            event=event,
            user=members[0],
            status=RSVPStatus.CANT_GO,
            attendance=AttendanceStatus.ATTENDED,
        )

        response = api_client.get("/api/community/events/attendance-report/", **_auth(events_admin))
        events = response.json()["events"]
        assert len(events) == 1
        assert events[0]["attended_count"] == 1

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

    def test_no_show_counts_split_by_event_type(self, api_client, host_user, members, events_admin):
        official = _make_event(
            host_user, "Official Event", days_ago=2, event_type=EventType.OFFICIAL
        )
        club = _make_event(host_user, "Club Event", days_ago=3, event_type=EventType.CLUB)
        community = _make_event(
            host_user, "Community Event", days_ago=4, event_type=EventType.COMMUNITY
        )
        for ev, count in ((official, 2), (club, 1), (community, 1)):
            for i in range(count):
                EventRSVP.objects.create(
                    event=ev,
                    user=members[i],
                    status=RSVPStatus.ATTENDING,
                    attendance=AttendanceStatus.DIDNT_GO,
                )

        response = api_client.get("/api/community/events/attendance-report/", **_auth(events_admin))
        data = response.json()
        assert data["official_no_show_count"] == 2
        assert data["club_no_show_count"] == 1
        row_types = {r["event_id"]: r["event_type"] for r in data["events"]}
        assert row_types[str(official.id)] == EventType.OFFICIAL
        assert row_types[str(club.id)] == EventType.CLUB


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
            attendance=AttendanceStatus.DIDNT_GO,
        )

        response = api_client.get("/api/auth/users/", **manage_users_headers)
        row = next(r for r in response.json() if r["id"] == str(members[0].pk))
        assert row["last_attended"] is None

    def test_last_attended_counts_mark_regardless_of_later_status_change(
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
        assert row["last_attended"] is not None

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

    def test_last_attended_excludes_draft_events(
        self, api_client, host_user, members, manage_users_headers
    ):
        draft = _make_event(host_user, "Draft Event", days_ago=2)
        EventRSVP.objects.create(
            event=draft,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        Event.objects.filter(pk=draft.pk).update(status=EventStatus.DRAFT)

        response = api_client.get("/api/auth/users/", **manage_users_headers)
        row = next(r for r in response.json() if r["id"] == str(members[0].pk))
        assert row["last_attended"] is None
