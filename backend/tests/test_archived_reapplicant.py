from datetime import datetime, timedelta

import pytest
from community.models import JoinRequest, JoinRequestStatus
from django.utils import timezone
from users.models import MembershipStatus, Role

from tests._users import make_user

pytestmark = pytest.mark.django_db

PHONE = "+16505551234"


@pytest.fixture
def archived_member(vettor_user):
    member = make_user(phone_number=PHONE, archived_at=timezone.now(), archived_by=vettor_user)
    member.roles.add(*Role.objects.filter(name="member", is_default=True))
    assert member.roles.exists()
    return member


def _decide(api_client, headers, join_request, status):
    response = api_client.patch(
        f"/api/community/join-requests/{join_request.id}/",
        {"status": status},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 200
    return response.json()


def test_archived_member_can_submit_join_form(api_client, why_join_id, archived_member):
    response = api_client.post(
        "/api/community/join-request/",
        {
            "first_name": "Coming",
            "last_name": "Back",
            "phone_number": PHONE,
            "email": "comingback@example.com",
            "answers": {why_join_id: "i want to return"},
            "sms_consent": True,
            "guidelines_consent": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    assert JoinRequest.objects.get(phone_number=PHONE).status == JoinRequestStatus.PENDING


def test_marking_tentative_unarchives(
    api_client, vettor_headers, sample_join_request, archived_member
):
    body = _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    archived_member.refresh_from_db()
    assert archived_member.membership_status == MembershipStatus.TENTATIVE
    assert archived_member.archived_at is None
    assert archived_member.archived_by is None
    assert not archived_member.roles.exists()

    login = api_client.get(f"/api/auth/magic-login/{body['magic_link_token']}/")
    assert login.status_code == 200


def test_tentative_then_approved_is_a_member(
    api_client, vettor_headers, sample_join_request, archived_member
):
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    archived_member.refresh_from_db()
    assert archived_member.membership_status == MembershipStatus.ACTIVE_MEMBER
    assert archived_member.roles.filter(name="member").exists()


@pytest.mark.parametrize(
    ("pause", "status"),
    [
        ({"is_paused": True}, MembershipStatus.GUIDELINES_PAUSED),
        ({"attendance_paused_at": timezone.now()}, MembershipStatus.ATTENDANCE_PAUSED),
    ],
)
def test_marking_tentative_keeps_an_archived_pause(
    api_client, vettor_headers, sample_join_request, pause, status
):
    paused = make_user(phone_number=PHONE, archived_at=timezone.now(), **pause)
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    paused.refresh_from_db()
    assert paused.membership_status == status
    assert paused.archived_at is None


def _listed(api_client, headers, join_request):
    response = api_client.get("/api/community/join-requests/", **headers)
    assert response.status_code == 200
    return next(r for r in response.json() if r["id"] == str(join_request.id))


def test_card_shows_who_archived_them_and_when(
    api_client, vettor_headers, sample_join_request, archived_member
):
    row = _listed(api_client, vettor_headers, sample_join_request)
    assert row["previously_archived"] is True
    assert row["previous_archive"]["archived_by_name"] == "Vettor"
    archived_at = datetime.fromisoformat(row["previous_archive"]["archived_at"])
    assert abs(archived_at - archived_member.archived_at) < timedelta(seconds=1)


def test_card_has_no_archive_for_a_first_time_applicant(
    api_client, vettor_headers, sample_join_request
):
    row = _listed(api_client, vettor_headers, sample_join_request)
    assert row["previously_archived"] is False
    assert row["previous_archive"] is None
