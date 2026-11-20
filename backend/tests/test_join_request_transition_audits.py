from datetime import timedelta

import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.models import (
    AttendanceStatus,
    EventType,
    JoinFormQuestion,
    JoinRequest,
    JoinRequestStatus,
    RejectionReason,
)
from django.test import TestCase
from django.utils import timezone
from users.models import MembershipStatus, User

from tests._auth import auth_headers_for
from tests._events import make_event, make_rsvp

pytestmark = pytest.mark.django_db


def _send(method, *args, **kwargs):
    with TestCase.captureOnCommitCallbacks(execute=True):
        return method(*args, **kwargs)


def _decide(api_client, headers, join_request, status, **extra):
    response = _send(
        api_client.patch,
        f"/api/community/join-requests/{join_request.id}/",
        {"status": status, **extra},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 200
    return response.json()


def _entry(action: str) -> AuditLogEntry:
    return AuditLogEntry.objects.get(action=action)


def test_submitted(api_client):
    rsvper = User.objects.create_user(
        phone_number="+14155550123", first_name="Sam", membership_status=MembershipStatus.NONE
    )
    body = {
        "first_name": "Sam",
        "last_name": "Green",
        "phone_number": "+14155550123",
        "email": "sam@example.com",
        "sms_consent": True,
        "guidelines_consent": True,
        "answers": {str(q.id): "x" for q in JoinFormQuestion.objects.filter(required=True)},
    }
    response = _send(
        api_client.post, "/api/community/join-request/", body, content_type="application/json"
    )
    assert response.status_code == 201

    entry = _entry("join_request_submitted")
    assert entry.target_id == str(JoinRequest.objects.get().id)
    assert entry.details["full_name"] == "Sam Green"
    assert entry.details["user_id"] == str(rsvper.pk)


def test_approved_names_user_linked_by_email(api_client, vettor_headers, sample_join_request):
    linked = User.objects.create_user(
        phone_number="+14155550199",
        email="sprout@example.com",
        first_name="Sprout",
        membership_status=MembershipStatus.NONE,
    )
    sample_join_request.user = linked
    sample_join_request.save(update_fields=["user"])

    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)

    assert _entry("join_request_approved").details["user_id"] == str(linked.pk)


@pytest.mark.parametrize("status", [JoinRequestStatus.TENTATIVE, JoinRequestStatus.APPROVED])
def test_admitted_names_actor_and_user(
    api_client, vettor_headers, vettor_user, sample_join_request, status
):
    _decide(api_client, vettor_headers, sample_join_request, status)

    user = User.objects.get(phone_number=sample_join_request.phone_number)
    entry = _entry(f"join_request_{status}")
    assert entry.actor == vettor_user
    assert entry.target_type == AuditTargetType.JOIN_REQUEST
    assert entry.target_id == str(sample_join_request.id)
    assert entry.details["user_id"] == str(user.pk)


def test_rejected_then_unrejected(api_client, vettor_headers, vettor_user, sample_join_request):
    rsvper = User.objects.create_user(
        phone_number=sample_join_request.phone_number,
        first_name="Sprout",
        membership_status=MembershipStatus.NONE,
    )
    _decide(
        api_client,
        vettor_headers,
        sample_join_request,
        JoinRequestStatus.REJECTED,
        rejection_reason=RejectionReason.NOT_VEGAN,
    )
    response = _send(
        api_client.patch,
        f"/api/community/join-requests/{sample_join_request.id}/unreject/",
        **vettor_headers,
    )
    assert response.status_code == 200

    rejected, unrejected = _entry("join_request_rejected"), _entry("join_request_unrejected")
    assert rejected.details["rejection_reason"] == RejectionReason.NOT_VEGAN
    for entry in (rejected, unrejected):
        assert entry.actor == vettor_user
        assert entry.target_id == str(sample_join_request.id)
        assert entry.details["user_id"] == str(rsvper.pk)


def test_reapproval_reactivates_archived_user(
    api_client, vettor_headers, vettor_user, sample_join_request
):
    archived = User.objects.create_user(
        phone_number=sample_join_request.phone_number,
        first_name="Prior",
        membership_status=MembershipStatus.ARCHIVED,
        archived_at=timezone.now(),
    )

    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)

    entry = _entry("user_reactivated")
    assert entry.actor == vettor_user
    assert (entry.target_type, entry.target_id) == (AuditTargetType.USER, str(archived.pk))
    assert entry.details["join_request_id"] == str(sample_join_request.id)
    assert entry.details["membership_status"] == MembershipStatus.ACTIVE_MEMBER


def _link_archived(join_request) -> User:
    linked = User.objects.create_user(
        phone_number="+14155550177",
        email="prior@example.com",
        first_name="Prior",
        membership_status=MembershipStatus.ARCHIVED,
        archived_at=timezone.now(),
    )
    join_request.user = linked
    join_request.save(update_fields=["user"])
    return linked


def test_reapproval_reactivates_linked_archived_user_with_other_phone(
    api_client, vettor_headers, sample_join_request
):
    linked = _link_archived(sample_join_request)

    body = _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)

    linked.refresh_from_db()
    assert linked.archived_at is None
    assert linked.membership_status == MembershipStatus.ACTIVE_MEMBER
    assert not User.objects.filter(phone_number=sample_join_request.phone_number).exists()
    assert body["user_id"] == str(linked.pk)
    assert body["magic_link_token"]
    assert _entry("user_reactivated").target_id == str(linked.pk)
    approved = _entry("join_request_approved").details
    assert (approved["user_id"], approved["user_created"]) == (str(linked.pk), True)


@pytest.mark.parametrize(
    "phone_match_fields",
    [
        {"membership_status": MembershipStatus.ACTIVE_MEMBER},
        {"membership_status": MembershipStatus.ARCHIVED, "archived_at": timezone.now()},
    ],
)
def test_reapproval_prefers_linked_archived_user_over_phone_match(
    api_client, vettor_headers, sample_join_request, phone_match_fields
):
    linked = _link_archived(sample_join_request)
    phone_match = User.objects.create_user(
        phone_number=sample_join_request.phone_number, first_name="Other", **phone_match_fields
    )

    body = _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)

    linked.refresh_from_db()
    assert linked.archived_at is None
    untouched = User.objects.get(pk=phone_match.pk)
    assert (untouched.membership_status, untouched.archived_at, untouched.first_name) == (
        phone_match.membership_status,
        phone_match.archived_at,
        "Other",
    )
    assert body["user_id"] == str(linked.pk)
    assert _entry("user_reactivated").target_id == str(linked.pk)
    assert _entry("join_request_approved").details["user_id"] == str(linked.pk)


def test_reapproval_records_pause_restored_from_archive(
    api_client, vettor_headers, sample_join_request
):
    User.objects.create_user(
        phone_number=sample_join_request.phone_number,
        first_name="Prior",
        membership_status=MembershipStatus.ARCHIVED,
        archived_at=timezone.now(),
        status_before_archive=MembershipStatus.ATTENDANCE_PAUSED,
    )

    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)

    entry = _entry("user_reactivated")
    assert entry.details["membership_status"] == MembershipStatus.ATTENDANCE_PAUSED


def test_check_in_approves_tentative(api_client):
    host = User.objects.create_user(phone_number="+12025557100", first_name="Host")
    user = User.objects.create_user(
        phone_number="+12025557101",
        first_name="Tent",
        membership_status=MembershipStatus.TENTATIVE,
    )
    join_request = JoinRequest.objects.create(
        phone_number=user.phone_number, user=user, status=JoinRequestStatus.TENTATIVE
    )
    event = make_event(
        event_type=EventType.OFFICIAL,
        start_datetime=timezone.now() - timedelta(hours=1),
        created_by=host,
    )
    make_rsvp(event, user)

    response = _send(
        api_client.post,
        f"/api/community/events/{event.id}/rsvps/{user.pk}/attendance/",
        {"attendance": AttendanceStatus.ATTENDED, "for_plus_one": False},
        content_type="application/json",
        **auth_headers_for(host),
    )
    assert response.status_code == 200

    entry = _entry("join_request_approved_via_check_in")
    assert entry.actor == host
    assert entry.target_id == str(join_request.id)
    assert entry.details["user_id"] == str(user.pk)
    assert entry.details["event_id"] == str(event.pk)
