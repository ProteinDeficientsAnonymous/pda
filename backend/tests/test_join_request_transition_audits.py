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
from users.models import User

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


@pytest.mark.parametrize("status", [JoinRequestStatus.TENTATIVE, JoinRequestStatus.APPROVED])
def test_admitted_names_actor_and_user(
    api_client, vettor_headers, vettor_user, sample_join_request, status
):
    body = _decide(api_client, vettor_headers, sample_join_request, status)

    entry = _entry(f"join_request_{status}")
    assert entry.actor == vettor_user
    assert entry.target_type == AuditTargetType.JOIN_REQUEST
    assert entry.target_id == str(sample_join_request.id)
    assert entry.details["user_id"] == body["user_id"]


def test_rejected_then_unrejected(api_client, vettor_headers, vettor_user, sample_join_request):
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


def test_reapproval_reactivates_archived_user(
    api_client, vettor_headers, vettor_user, sample_join_request
):
    archived = User.objects.create_user(
        phone_number=sample_join_request.phone_number, first_name="Prior"
    )
    archived.archived_at = timezone.now()
    archived.save(update_fields=["archived_at"])

    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)

    entry = _entry("user_reactivated")
    assert entry.actor == vettor_user
    assert (entry.target_type, entry.target_id) == (AuditTargetType.USER, str(archived.pk))
    assert entry.details["join_request_id"] == str(sample_join_request.id)


def test_check_in_approves_tentative(api_client):
    host = User.objects.create_user(phone_number="+12025557100", first_name="Host")
    user = User.objects.create_user(phone_number="+12025557101", first_name="Tent", is_member=False)
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
