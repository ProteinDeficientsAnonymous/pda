from datetime import timedelta

import pytest
from audit.models import AuditLogEntry
from community.models import AttendanceStatus, EventType, JoinRequest, JoinRequestStatus
from django.utils import timezone
from users.models import User
from users.roles import Role

from tests._auth import auth_headers_for
from tests._events import make_event, make_rsvp


@pytest.fixture
def host(db):
    return User.objects.create_user(phone_number="+12025557100", first_name="Host")


@pytest.fixture
def paused(db):
    user = User.objects.create_user(phone_number="+12025557101", first_name="Paused")
    user.roles.clear()
    user.attendance_paused_at = timezone.now() - timedelta(days=10)
    user.attendance_grace_notified_at = timezone.now() - timedelta(days=20)
    user.is_member = False
    user.save(update_fields=["attendance_paused_at", "attendance_grace_notified_at", "is_member"])
    return user


def _attended(user, *, event_type=EventType.OFFICIAL, days_ago=30):
    event = make_event(
        event_type=event_type, start_datetime=timezone.now() - timedelta(days=days_ago)
    )
    make_rsvp(event, user, attendance=AttendanceStatus.ATTENDED)


def _check_in(api_client, host, user, *, event_type=EventType.OFFICIAL, for_plus_one=False):
    event = make_event(
        event_type=event_type, start_datetime=timezone.now() - timedelta(hours=1), created_by=host
    )
    make_rsvp(event, user, has_plus_one=for_plus_one)
    resp = api_client.post(
        f"/api/community/events/{event.id}/rsvps/{user.pk}/attendance/",
        {"attendance": AttendanceStatus.ATTENDED, "for_plus_one": for_plus_one},
        content_type="application/json",
        **auth_headers_for(host),
    )
    assert resp.status_code == 200
    user.refresh_from_db()


@pytest.mark.django_db
class TestRestoreOnCheckIn:
    def test_first_qualifying_check_in_does_not_restore(self, api_client, host, paused):
        _check_in(api_client, host, paused)
        assert paused.attendance_paused_at is not None
        assert paused.is_member is False

    def test_second_qualifying_check_in_restores(
        self, api_client, host, paused, django_capture_on_commit_callbacks
    ):
        _attended(paused, event_type=EventType.CLUB)
        with django_capture_on_commit_callbacks(execute=True):
            _check_in(api_client, host, paused)

        assert paused.attendance_paused_at is None
        assert paused.attendance_grace_notified_at is None
        assert paused.restored_at is not None
        assert paused.is_member is True
        assert (
            paused.roles.filter(name="member").exists()
            == Role.objects.filter(name="member", is_default=True).exists()
        )
        assert AuditLogEntry.objects.filter(
            action="user_attendance_restored", target_id=str(paused.pk)
        ).exists()

    def test_qualifying_event_older_than_a_year_does_not_count(self, api_client, host, paused):
        _attended(paused, days_ago=400)
        _check_in(api_client, host, paused)
        assert paused.attendance_paused_at is not None

    def test_community_event_check_in_never_restores(self, api_client, host, paused):
        _attended(paused)
        _attended(paused)
        _check_in(api_client, host, paused, event_type=EventType.COMMUNITY)
        assert paused.attendance_paused_at is not None

    def test_plus_one_check_in_never_restores(self, api_client, host, paused):
        _attended(paused)
        _attended(paused)
        _check_in(api_client, host, paused, for_plus_one=True)
        assert paused.attendance_paused_at is not None

    def test_stale_tentative_request_does_not_promote_on_first(self, api_client, host, paused):
        jr = JoinRequest.objects.create(
            first_name="Paused",
            phone_number=paused.phone_number,
            user=paused,
            status=JoinRequestStatus.TENTATIVE,
        )
        _check_in(api_client, host, paused)

        assert paused.is_member is False
        jr.refresh_from_db()
        assert jr.status == JoinRequestStatus.TENTATIVE
