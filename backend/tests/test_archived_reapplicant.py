from datetime import datetime, timedelta

import pytest
from community.join_requests.approval import maybe_promote_tentative
from community.models import JoinRequest, JoinRequestEvent, JoinRequestStatus
from community.validation import Code
from django.utils import timezone
from users.models import MembershipStatus, Role, User

from tests._asserts import assert_error_code
from tests._tentative_helpers import open_official_event
from tests._users import make_user

__all__ = ["open_official_event"]

pytestmark = pytest.mark.django_db

PHONE = "+16505551234"

_STATUS_TO_EVENT = {
    JoinRequestStatus.TENTATIVE: JoinRequestEvent.MARK_TENTATIVE,
    JoinRequestStatus.APPROVED: JoinRequestEvent.APPROVE,
    JoinRequestStatus.REJECTED: JoinRequestEvent.REJECT,
}


@pytest.fixture
def archived_member(vettor_user):
    member = make_user(
        phone_number=PHONE, archived_at=timezone.now(), membership_status_changed_by=vettor_user
    )
    member.roles.add(*Role.objects.filter(name="member", is_default=True))
    assert member.roles.exists()
    return member


def _patch_status(api_client, headers, join_request, status):
    return api_client.patch(
        f"/api/community/join-requests/{join_request.id}/",
        {"event": _STATUS_TO_EVENT[status]},
        content_type="application/json",
        **headers,
    )


def _decide(api_client, headers, join_request, status):
    response = _patch_status(api_client, headers, join_request, status)
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


def test_marking_tentative_keeps_an_archived_attendance_pause(
    api_client, vettor_headers, sample_join_request
):
    paused = make_user(
        phone_number=PHONE,
        archived_at=timezone.now(),
        attendance_paused_at=timezone.now(),
        status_before_archive=MembershipStatus.ATTENDANCE_PAUSED,
    )
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    paused.refresh_from_db()
    assert paused.membership_status == MembershipStatus.ATTENDANCE_PAUSED
    assert paused.archived_at is None
    assert paused.status_before_archive is None


@pytest.mark.parametrize("decision", [JoinRequestStatus.TENTATIVE, JoinRequestStatus.APPROVED])
def test_vetting_refuses_an_applicant_archived_while_guidelines_paused(
    api_client, vettor_headers, sample_join_request, decision
):
    paused = make_user(
        phone_number=PHONE,
        archived_at=timezone.now(),
        status_before_archive=MembershipStatus.GUIDELINES_PAUSED,
    )
    response = _patch_status(api_client, vettor_headers, sample_join_request, decision)
    assert response.status_code == 400
    assert_error_code(response, Code.JoinRequest.APPLICANT_GUIDELINES_PAUSED)
    sample_join_request.refresh_from_db()
    assert sample_join_request.status == JoinRequestStatus.PENDING
    assert sample_join_request.status_changed_by is None
    assert sample_join_request.user is None
    paused.refresh_from_db()
    assert paused.archived_at is not None
    assert paused.status_before_archive == MembershipStatus.GUIDELINES_PAUSED


@pytest.mark.parametrize("paused", ["linked", "phone_match"])
def test_approval_checks_a_linked_archived_account_and_the_phone_match(
    api_client, vettor_headers, sample_join_request, paused
):
    pause = {"archived_at": timezone.now(), "status_before_archive": "guidelines_paused"}
    linked_pause = pause if paused == "linked" else {"archived_at": timezone.now()}
    sample_join_request.user = make_user(phone_number="+16505559999", **linked_pause)
    sample_join_request.save(update_fields=["user"])
    if paused == "phone_match":
        make_user(phone_number=PHONE, **pause)
    response = _patch_status(
        api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED
    )
    assert_error_code(response, Code.JoinRequest.APPLICANT_GUIDELINES_PAUSED)
    assert not User.objects.filter(phone_number=PHONE, archived_at__isnull=True).exists()


def test_a_paused_phone_match_does_not_block_a_linked_rsvper(
    api_client, vettor_headers, sample_join_request
):
    sample_join_request.user = make_user(
        phone_number="+16505559999", membership_status=MembershipStatus.NONE
    )
    sample_join_request.save(update_fields=["user"])
    make_user(phone_number=PHONE, membership_status=MembershipStatus.GUIDELINES_PAUSED)
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)


def test_approving_a_tentative_who_is_guidelines_paused_is_refused(
    api_client, vettor_headers, sample_join_request
):
    paused = make_user(phone_number=PHONE, membership_status=MembershipStatus.GUIDELINES_PAUSED)
    sample_join_request.status = JoinRequestStatus.TENTATIVE
    sample_join_request.user = paused
    sample_join_request.save(update_fields=["status", "user"])
    response = _patch_status(
        api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED
    )
    assert_error_code(response, Code.JoinRequest.APPLICANT_GUIDELINES_PAUSED)
    sample_join_request.refresh_from_db()
    assert sample_join_request.status == JoinRequestStatus.TENTATIVE


def test_approving_an_archived_applicant_reactivates_them(
    api_client, vettor_headers, sample_join_request, archived_member
):
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    archived_member.refresh_from_db()
    assert archived_member.membership_status == MembershipStatus.ACTIVE_MEMBER
    assert archived_member.archived_at is None


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
    assert row["previous_archive"]["paused_status"] is None


@pytest.mark.parametrize(
    "status", [MembershipStatus.GUIDELINES_PAUSED, MembershipStatus.ATTENDANCE_PAUSED]
)
def test_card_names_the_pause_they_were_archived_under(
    api_client, vettor_headers, sample_join_request, status
):
    make_user(phone_number=PHONE, archived_at=timezone.now(), status_before_archive=status)
    row = _listed(api_client, vettor_headers, sample_join_request)
    assert row["previous_archive"]["paused_status"] == status


def test_card_has_no_archive_for_a_first_time_applicant(
    api_client, vettor_headers, sample_join_request
):
    row = _listed(api_client, vettor_headers, sample_join_request)
    assert row["previously_archived"] is False
    assert row["previous_archive"] is None


def test_check_in_does_not_promote_a_guidelines_paused_tentative(
    sample_join_request, vettor_user, open_official_event
):
    paused = make_user(phone_number=PHONE, membership_status=MembershipStatus.GUIDELINES_PAUSED)
    sample_join_request.status = JoinRequestStatus.TENTATIVE
    sample_join_request.user = paused
    sample_join_request.save(update_fields=["status", "user"])
    assert not maybe_promote_tentative(paused, open_official_event, vettor_user)
    assert paused.membership_status == MembershipStatus.GUIDELINES_PAUSED
