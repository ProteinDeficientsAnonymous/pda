"""Tests for the admin member attendance analytics endpoint."""

from datetime import timedelta

import pytest
from community.models import (
    AttendanceStatus,
    Event,
    EventRSVP,
    EventStatus,
    EventType,
    FeatureFlag,
    FeatureFlagState,
    RSVPStatus,
)
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken

MEMBERS_URL = "/api/community/events/attendance-analytics/members/"


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture
def flag_on(db):
    FeatureFlagState.objects.create(key=FeatureFlag.ADMIN_ATTENDANCE_ANALYTICS, enabled=True)


@pytest.fixture
def member(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+12025551900",
        password="x",
        first_name="Member",
        last_name="One",
        is_member=True,
    )


@pytest.fixture
def host_user(db):
    from users.models import User

    return User.objects.create_user(phone_number="+12025551800", password="x", first_name="Host")


@pytest.fixture
def events_admin(db):
    from users.models import Role, User
    from users.permissions import PermissionKey

    admin = User.objects.create_user(phone_number="+12025551801", password="x", first_name="Admin")
    role = Role.objects.create(name="events_admin", permissions=[PermissionKey.MANAGE_EVENTS])
    admin.roles.add(role)
    return admin


def _make_event(host_user, title, days_ago, event_type=EventType.CLUB):
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
class TestMemberAttendanceAnalyticsEndpoint:
    def test_requires_flag(self, api_client, events_admin, member):
        response = api_client.get(MEMBERS_URL, **_auth(events_admin))
        assert response.status_code == 403

    def test_requires_manage_events_permission(self, api_client, flag_on, member):
        response = api_client.get(MEMBERS_URL, **_auth(member))
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client, flag_on):
        response = api_client.get(MEMBERS_URL)
        assert response.status_code == 401

    def test_qualifying_count_and_last_date(
        self, api_client, flag_on, host_user, member, events_admin
    ):
        older = _make_event(host_user, "Older Club", days_ago=100, event_type=EventType.CLUB)
        newer = _make_event(host_user, "Newer Official", days_ago=10, event_type=EventType.OFFICIAL)
        for ev in (older, newer):
            EventRSVP.objects.create(
                event=ev,
                user=member,
                status=RSVPStatus.ATTENDING,
                attendance=AttendanceStatus.ATTENDED,
            )

        response = api_client.get(MEMBERS_URL, **_auth(events_admin))
        assert response.status_code == 200
        row = next(r for r in response.json()["members"] if r["user_id"] == str(member.pk))
        assert row["qualifying_count_12mo"] == 2
        assert row["last_qualifying_at"][:10] == newer.start_datetime.date().isoformat()
        assert row["compliant"] is True

    def test_community_event_never_counts_as_qualifying(
        self, api_client, flag_on, host_user, member, events_admin
    ):
        community_event = _make_event(
            host_user, "Community Hang", days_ago=5, event_type=EventType.COMMUNITY
        )
        EventRSVP.objects.create(
            event=community_event,
            user=member,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )

        response = api_client.get(MEMBERS_URL, **_auth(events_admin))
        row = next(r for r in response.json()["members"] if r["user_id"] == str(member.pk))
        assert row["qualifying_count_12mo"] == 0
        assert row["community_count"] == 1
        assert row["compliant"] is False

    def test_outside_12mo_window_excluded_from_count(
        self, api_client, flag_on, host_user, member, events_admin
    ):
        old_event = _make_event(host_user, "Ancient Club", days_ago=400, event_type=EventType.CLUB)
        EventRSVP.objects.create(
            event=old_event,
            user=member,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )

        response = api_client.get(MEMBERS_URL, **_auth(events_admin))
        row = next(r for r in response.json()["members"] if r["user_id"] == str(member.pk))
        assert row["qualifying_count_12mo"] == 0
        # last_qualifying_at is not window-bound — it's the true last attendance.
        assert row["last_qualifying_at"] is not None
        assert row["is_pause_candidate"] is True

    def test_no_show_and_cancel_counts(self, api_client, flag_on, host_user, member, events_admin):
        event = _make_event(host_user, "No Show Event", days_ago=5)
        EventRSVP.objects.create(
            event=event,
            user=member,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.NO_SHOW,
        )
        cancelled_event = _make_event(host_user, "Cancelled RSVP Event", days_ago=3)
        EventRSVP.objects.create(
            event=cancelled_event,
            user=member,
            status=RSVPStatus.CANT_GO,
            cancelled_at=timezone.now(),
        )

        response = api_client.get(MEMBERS_URL, **_auth(events_admin))
        row = next(r for r in response.json()["members"] if r["user_id"] == str(member.pk))
        assert row["no_show_count"] == 1
        assert row["cancel_count"] == 1

    def test_never_attended_is_pause_candidate(
        self, api_client, flag_on, host_user, member, events_admin
    ):
        response = api_client.get(MEMBERS_URL, **_auth(events_admin))
        row = next(r for r in response.json()["members"] if r["user_id"] == str(member.pk))
        assert row["last_qualifying_at"] is None
        assert row["is_pause_candidate"] is True

    def test_pause_candidates_sorted_first(self, api_client, flag_on, host_user, events_admin):
        from users.models import User

        compliant = User.objects.create_user(
            phone_number="+12025552000", password="x", first_name="Compliant", is_member=True
        )
        candidate = User.objects.create_user(
            phone_number="+12025552001", password="x", first_name="Candidate", is_member=True
        )
        recent = _make_event(host_user, "Recent", days_ago=5)
        EventRSVP.objects.create(
            event=recent,
            user=compliant,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )

        response = api_client.get(MEMBERS_URL, **_auth(events_admin))
        ids = [r["user_id"] for r in response.json()["members"]]
        assert ids.index(str(candidate.pk)) < ids.index(str(compliant.pk))

    def test_paused_member_included_and_labeled(self, api_client, flag_on, host_user, events_admin):
        from users.models import User

        paused = User.objects.create_user(
            phone_number="+12025552002",
            password="x",
            first_name="Paused",
            is_member=True,
            is_paused=True,
        )
        response = api_client.get(MEMBERS_URL, **_auth(events_admin))
        row = next(r for r in response.json()["members"] if r["user_id"] == str(paused.pk))
        assert row["is_paused"] is True

    def test_archived_member_excluded(self, api_client, flag_on, events_admin):
        from users.models import User

        archived = User.objects.create_user(
            phone_number="+12025552003",
            password="x",
            first_name="Archived",
            is_member=True,
            archived_at=timezone.now(),
        )
        response = api_client.get(MEMBERS_URL, **_auth(events_admin))
        ids = [r["user_id"] for r in response.json()["members"]]
        assert str(archived.pk) not in ids

    def test_non_member_excluded(self, api_client, flag_on, events_admin):
        from users.models import User

        guest = User.objects.create_user(
            phone_number="+12025552004", password="x", first_name="Guest", is_member=False
        )
        response = api_client.get(MEMBERS_URL, **_auth(events_admin))
        ids = [r["user_id"] for r in response.json()["members"]]
        assert str(guest.pk) not in ids

    def test_stranded_mark_after_rsvp_change_not_counted(
        self, api_client, flag_on, host_user, member, events_admin
    ):
        event = _make_event(host_user, "Flipped Event", days_ago=2)
        EventRSVP.objects.create(
            event=event,
            user=member,
            status=RSVPStatus.CANT_GO,
            attendance=AttendanceStatus.ATTENDED,
        )
        response = api_client.get(MEMBERS_URL, **_auth(events_admin))
        row = next(r for r in response.json()["members"] if r["user_id"] == str(member.pk))
        assert row["qualifying_count_12mo"] == 0
        assert row["last_qualifying_at"] is None
