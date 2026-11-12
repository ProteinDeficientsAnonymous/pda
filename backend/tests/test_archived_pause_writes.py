from datetime import timedelta

import pytest
from community.models import Event, EventStatus, JoinRequestStatus
from django.utils import timezone
from users.models import MembershipStatus

from tests._users import make_attendance_paused, make_user

pytestmark = pytest.mark.django_db


def _patch(api_client, headers, user, body):
    response = api_client.patch(
        f"/api/auth/users/{user.pk}/", body, content_type="application/json", **headers
    )
    assert response.status_code == 200
    user.refresh_from_db()
    return user


def _archive(api_client, headers, user):
    response = api_client.delete(f"/api/auth/users/{user.pk}/", **headers)
    assert response.status_code == 204
    user.refresh_from_db()
    return user


@pytest.mark.parametrize(
    ("make", "body", "before"),
    [
        (make_user, {"attendance_paused": True}, MembershipStatus.ATTENDANCE_PAUSED),
        (make_attendance_paused, {"attendance_paused": False}, MembershipStatus.ACTIVE_MEMBER),
        (make_user, {"guidelines_paused": True}, MembershipStatus.GUIDELINES_PAUSED),
        (
            lambda **f: make_user(membership_status=MembershipStatus.GUIDELINES_PAUSED, **f),
            {"guidelines_paused": False},
            MembershipStatus.ATTENDANCE_PAUSED,
        ),
    ],
    ids=["attendance-pause", "attendance-unpause", "guidelines-pause", "guidelines-unpause"],
)
def test_pause_writers_leave_an_archived_user_archived(
    api_client, manage_users_headers, make, body, before
):
    user = _archive(api_client, manage_users_headers, make(last_login=timezone.now()))
    archived_at = user.membership_status_changed_at
    user = _patch(api_client, manage_users_headers, user, body)
    assert user.membership_status == MembershipStatus.ARCHIVED
    assert user.status_before_archive == before
    assert user.is_guidelines_paused is (before == MembershipStatus.GUIDELINES_PAUSED)
    assert user.membership_status_changed_at == archived_at


@pytest.mark.parametrize("body", [{"attendance_paused": True}, {"guidelines_paused": True}])
def test_pausing_an_archived_host_keeps_their_events(api_client, manage_users_headers, body):
    host = make_user(last_login=timezone.now())
    event = Event.objects.create(
        title="potluck", start_datetime=timezone.now() + timedelta(days=3), created_by=host
    )
    event.co_hosts.add(host)
    _patch(api_client, manage_users_headers, _archive(api_client, manage_users_headers, host), body)
    event.refresh_from_db()
    assert event.status == EventStatus.ACTIVE


def test_guidelines_paused_while_archived_comes_back_paused(
    api_client, manage_users_headers, vettor_headers, sample_join_request
):
    member = make_user(phone_number=sample_join_request.phone_number, last_login=timezone.now())
    member = _archive(api_client, manage_users_headers, member)
    _patch(api_client, manage_users_headers, member, {"guidelines_paused": True})
    response = api_client.patch(
        f"/api/community/join-requests/{sample_join_request.id}/",
        {"status": JoinRequestStatus.APPROVED},
        content_type="application/json",
        **vettor_headers,
    )
    assert response.status_code == 200
    member.refresh_from_db()
    assert member.membership_status == MembershipStatus.GUIDELINES_PAUSED
    assert member.archived_at is None
