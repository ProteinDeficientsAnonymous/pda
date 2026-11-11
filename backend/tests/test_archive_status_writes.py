import pytest
from django.utils import timezone
from users.models import MembershipStatus

from tests._auth import auth_headers_for
from tests._users import make_user

pytestmark = pytest.mark.django_db


def test_admin_archive_writes_archived(api_client, manage_users_headers):
    member = make_user(last_login=timezone.now())
    response = api_client.delete(f"/api/auth/users/{member.pk}/", **manage_users_headers)
    assert response.status_code == 204
    member.refresh_from_db()
    assert member.membership_status == MembershipStatus.ARCHIVED
    assert member.status_before_archive == MembershipStatus.ACTIVE_MEMBER
    assert member.membership_status_changed_at is not None


def test_self_delete_writes_archived(api_client):
    member = make_user(password="testpass123")
    response = api_client.post(
        "/api/auth/me/delete/",
        {"password": "testpass123"},
        content_type="application/json",
        **auth_headers_for(member),
    )
    assert response.status_code == 204
    member.refresh_from_db()
    assert member.membership_status == MembershipStatus.ARCHIVED
    assert member.status_before_archive == MembershipStatus.ACTIVE_MEMBER
