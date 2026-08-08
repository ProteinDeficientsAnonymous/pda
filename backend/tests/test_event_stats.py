"""Tests for host-only event stats, attendance marking, and cancellation lead time."""

from datetime import timedelta

import pytest
from community._event_helpers import _cancellations
from community._event_rsvps import _resolve_cancelled_at
from community._rsvp_counts import (
    _attended_count,
    _didnt_go_count,
    _no_response_count,
)
from community.models import AttendanceStatus, Event, EventRSVP, RSVPStatus
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import Role, User
from users.permissions import PermissionKey


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture
def members(db):
    return [
        User.objects.create_user(
            phone_number=f"+1202555090{i}",
            password="x",
            first_name=f"Member {i}",
        )
        for i in range(1, 5)
    ]


@pytest.fixture
def host_user(db):
    return User.objects.create_user(
        phone_number="+12025558000",
        password="x",
        first_name="Host",
    )


@pytest.fixture
def cohost_user(db):
    return User.objects.create_user(
        phone_number="+12025558001",
        password="x",
        first_name="Co-host",
    )


@pytest.fixture
def admin_user(db):
    admin = User.objects.create_user(
        phone_number="+12025558002",
        password="x",
        first_name="Event",
        last_name="Admin",
    )
    role = Role.objects.create(name="stats_admin", permissions=[PermissionKey.MANAGE_EVENTS])
    admin.roles.add(role)
    return admin


@pytest.fixture
def stats_event(db, host_user, cohost_user, members):
    event = Event.objects.create(
        title="Stats Event",
        start_datetime=timezone.now() + timedelta(days=7),
        end_datetime=timezone.now() + timedelta(days=7, hours=2),
        rsvp_enabled=True,
        created_by=host_user,
    )
    event.co_hosts.add(cohost_user)
    event.invited_users.set(members)
    return event


@pytest.fixture
def open_check_in_event(db, host_user, cohost_user, members):
    """Event starting in 30 min — check-in window is open."""
    event = Event.objects.create(
        title="Check-in Open Event",
        start_datetime=timezone.now() + timedelta(minutes=30),
        end_datetime=timezone.now() + timedelta(hours=2),
        rsvp_enabled=True,
        created_by=host_user,
    )
    event.co_hosts.add(cohost_user)
    event.invited_users.set(members)
    return event


@pytest.mark.django_db
class TestNoResponseCount:
    def test_invited_with_no_rsvp_are_counted(self, stats_event, members):
        EventRSVP.objects.create(event=stats_event, user=members[0], status=RSVPStatus.ATTENDING)
        stats_event = Event.objects.prefetch_related("invited_users", "rsvps").get(
            pk=stats_event.pk
        )
        assert _no_response_count(stats_event) == 3

    def test_user_with_rsvp_not_counted_as_no_response(self, stats_event, members):
        for m in members:
            EventRSVP.objects.create(event=stats_event, user=m, status=RSVPStatus.ATTENDING)
        stats_event = Event.objects.prefetch_related("invited_users", "rsvps").get(
            pk=stats_event.pk
        )
        assert _no_response_count(stats_event) == 0


@pytest.mark.django_db
class TestCancellations:
    def test_lead_time_derived_from_cancelled_at(self, stats_event, members):
        rsvp = EventRSVP.objects.create(
            event=stats_event, user=members[0], status=RSVPStatus.CANT_GO
        )
        cancelled_at = stats_event.start_datetime - timedelta(days=3)
        # updated_at later than cancelled_at: lead-time must track the cancel time.
        EventRSVP.objects.filter(pk=rsvp.pk).update(
            cancelled_at=cancelled_at,
            updated_at=stats_event.start_datetime - timedelta(hours=1),
        )
        stats_event = Event.objects.prefetch_related("invited_users", "rsvps__user").get(
            pk=stats_event.pk
        )
        rows = _cancellations(stats_event)
        assert len(rows) == 1
        assert rows[0].user_id == str(members[0].pk)
        assert rows[0].cancelled_at == cancelled_at
        assert rows[0].days_before_event == 3

    def test_lead_time_falls_back_to_updated_at_when_cancelled_at_missing(
        self, stats_event, members
    ):
        rsvp = EventRSVP.objects.create(
            event=stats_event, user=members[0], status=RSVPStatus.CANT_GO
        )
        EventRSVP.objects.filter(pk=rsvp.pk).update(
            cancelled_at=None,
            updated_at=stats_event.start_datetime - timedelta(days=2),
        )
        stats_event = Event.objects.prefetch_related("invited_users", "rsvps__user").get(
            pk=stats_event.pk
        )
        rows = _cancellations(stats_event)
        assert rows[0].days_before_event == 2

    def test_excludes_attending_users(self, stats_event, members):
        EventRSVP.objects.create(event=stats_event, user=members[0], status=RSVPStatus.ATTENDING)
        EventRSVP.objects.create(event=stats_event, user=members[1], status=RSVPStatus.CANT_GO)
        stats_event = Event.objects.prefetch_related("invited_users", "rsvps__user").get(
            pk=stats_event.pk
        )
        rows = _cancellations(stats_event)
        assert len(rows) == 1
        assert rows[0].user_id == str(members[1].pk)

    def test_empty_when_no_start_datetime(self, host_user, members):
        event = Event.objects.create(
            title="TBD Event",
            datetime_tbd=True,
            rsvp_enabled=True,
            created_by=host_user,
        )
        EventRSVP.objects.create(event=event, user=members[0], status=RSVPStatus.CANT_GO)
        event = Event.objects.prefetch_related("invited_users", "rsvps__user").get(pk=event.pk)
        assert _cancellations(event) == []


@pytest.mark.django_db
class TestResolveCancelledAt:
    def test_stamps_on_transition_into_cant_go(self, stats_event, members):
        rsvp = EventRSVP.objects.create(
            event=stats_event, user=members[0], status=RSVPStatus.ATTENDING
        )
        assert _resolve_cancelled_at(rsvp, RSVPStatus.CANT_GO) is not None

    def test_stamps_for_brand_new_cant_go(self):
        assert _resolve_cancelled_at(None, RSVPStatus.CANT_GO) is not None

    def test_clears_when_leaving_cant_go(self, stats_event, members):
        cancelled = stats_event.start_datetime - timedelta(days=1)
        rsvp = EventRSVP.objects.create(
            event=stats_event,
            user=members[0],
            status=RSVPStatus.CANT_GO,
            cancelled_at=cancelled,
        )
        assert _resolve_cancelled_at(rsvp, RSVPStatus.ATTENDING) is None

    def test_preserves_original_cancel_time_when_still_cant_go(self, stats_event, members):
        cancelled = stats_event.start_datetime - timedelta(days=5)
        rsvp = EventRSVP.objects.create(
            event=stats_event,
            user=members[0],
            status=RSVPStatus.CANT_GO,
            cancelled_at=cancelled,
        )
        assert _resolve_cancelled_at(rsvp, RSVPStatus.CANT_GO) == cancelled


@pytest.mark.django_db
class TestAttendanceCounts:
    def test_attended_no_show_only_count_going(self, stats_event, members):
        EventRSVP.objects.create(
            event=stats_event,
            user=members[0],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        EventRSVP.objects.create(
            event=stats_event,
            user=members[1],
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.DIDNT_GO,
        )
        # cant_go marked attended shouldn't count (defensive)
        EventRSVP.objects.create(
            event=stats_event,
            user=members[2],
            status=RSVPStatus.CANT_GO,
            attendance=AttendanceStatus.ATTENDED,
        )
        stats_event = Event.objects.prefetch_related("invited_users", "rsvps__user").get(
            pk=stats_event.pk
        )
        assert _attended_count(stats_event) == 1
        assert _didnt_go_count(stats_event) == 1
