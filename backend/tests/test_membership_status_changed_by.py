import pytest
from community.models import JoinRequestStatus
from django.utils import timezone
from users.models import MembershipStatus, User

from tests._auth import auth_headers_for
from tests._public_rsvp_helpers import make_official_event, post
from tests._users import make_user

pytestmark = pytest.mark.django_db

NEW_PHONE = "+12025550777"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/api/auth/create-user/",
            {"phone_number": NEW_PHONE, "first_name": "New", "email": "new@example.com"},
        ),
        ("/api/auth/bulk-create-users/", {"phone_numbers": [NEW_PHONE]}),
    ],
    ids=["single", "bulk"],
)
def test_admin_create_records_the_creator(
    api_client, manage_users_user, manage_users_headers, path, payload
):
    response = api_client.post(
        path, payload, content_type="application/json", **manage_users_headers
    )
    assert response.status_code in (200, 201)
    created = User.objects.get(phone_number=NEW_PHONE)
    assert created.membership_status_changed_by == manage_users_user
    assert created.membership_status_changed_at is not None


@pytest.mark.parametrize("decision", [JoinRequestStatus.TENTATIVE, JoinRequestStatus.APPROVED])
def test_vetting_a_new_applicant_records_the_vetter(
    api_client, vettor_user, vettor_headers, sample_join_request, decision
):
    response = api_client.patch(
        f"/api/community/join-requests/{sample_join_request.id}/",
        {"status": decision},
        content_type="application/json",
        **vettor_headers,
    )
    assert response.status_code == 200
    user = User.objects.get(phone_number=sample_join_request.phone_number)
    assert user.membership_status_changed_by == vettor_user


@pytest.mark.parametrize("decision", [JoinRequestStatus.TENTATIVE, JoinRequestStatus.APPROVED])
@pytest.mark.parametrize("status", [MembershipStatus.NONE, MembershipStatus.ARCHIVED])
def test_vetting_an_existing_account_records_the_vetter(
    api_client, vettor_user, sample_join_request, decision, status
):
    archived_at = timezone.now() if status == MembershipStatus.ARCHIVED else None
    existing = make_user(
        phone_number=sample_join_request.phone_number,
        membership_status=status,
        archived_at=archived_at,
    )
    sample_join_request.user = existing
    sample_join_request.save(update_fields=["user"])
    response = api_client.patch(
        f"/api/community/join-requests/{sample_join_request.id}/",
        {"status": decision},
        content_type="application/json",
        **auth_headers_for(vettor_user),
    )
    assert response.status_code == 200
    existing.refresh_from_db()
    assert existing.membership_status != status
    assert existing.membership_status_changed_by == vettor_user


def test_public_rsvp_stamps_no_actor(api_client):
    assert post(api_client, make_official_event()).status_code in (200, 201)
    rsvper = User.objects.get(membership_status=MembershipStatus.NONE)
    assert rsvper.membership_status_changed_at is not None
    assert rsvper.membership_status_changed_by is None


def test_unchanged_status_keeps_the_stamp():
    member = make_user()
    member.set_membership_status(MembershipStatus.ACTIVE_MEMBER, by=member)
    assert member.membership_status_changed_at is None


@pytest.mark.parametrize(
    ("make", "body"),
    [
        (make_user, {"attendance_paused": True}),
        (make_user, {"guidelines_paused": True}),
        (
            lambda: make_user(membership_status=MembershipStatus.GUIDELINES_PAUSED),
            {"guidelines_paused": False},
        ),
    ],
    ids=["attendance-pause", "guidelines-pause", "guidelines-unpause"],
)
def test_pause_changes_record_the_admin(
    api_client, manage_users_user, manage_users_headers, make, body
):
    member = make()
    response = api_client.patch(
        f"/api/auth/users/{member.pk}/",
        body,
        content_type="application/json",
        **manage_users_headers,
    )
    assert response.status_code == 200
    member.refresh_from_db()
    assert member.membership_status_changed_by == manage_users_user


def test_archive_records_the_admin(api_client, manage_users_user, manage_users_headers):
    member = make_user(last_login=timezone.now())
    response = api_client.delete(f"/api/auth/users/{member.pk}/", **manage_users_headers)
    assert response.status_code == 204
    member.refresh_from_db()
    assert member.membership_status_changed_by == manage_users_user


def test_self_delete_records_the_user(api_client):
    member = make_user(password="testpass123")
    response = api_client.post(
        "/api/auth/me/delete/",
        {"password": "testpass123"},
        content_type="application/json",
        **auth_headers_for(member),
    )
    assert response.status_code == 204
    member.refresh_from_db()
    assert member.membership_status_changed_by == member
