import pytest
from community.validation import Code
from django.utils import timezone
from users.models import MagicLoginToken, MembershipStatus

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._users import make_user

pytestmark = pytest.mark.django_db

PASSWORD = "Sprout-pass-123!"


@pytest.fixture
def non_member(db):
    return make_user(
        password=PASSWORD,
        membership_status=MembershipStatus.NONE,
        guidelines_consent_at=timezone.now(),
    )


def test_non_member_without_rejection_is_blocked(api_client, non_member):
    magic = MagicLoginToken.create_for_user(non_member)
    response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
    assert response.status_code == 403
    assert_error_code(response, Code.Auth.NOT_A_MEMBER)


def test_non_member_password_login_is_blocked(api_client, non_member):
    response = api_client.post(
        "/api/auth/login/",
        {"phone_number": non_member.phone_number, "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 403
    assert_error_code(response, Code.Auth.NOT_A_MEMBER)


def test_non_member_cannot_finish_onboarding(api_client, non_member):
    non_member.needs_onboarding = True
    non_member.save(update_fields=["needs_onboarding"])
    response = api_client.post(
        "/api/auth/complete-onboarding/",
        {"new_password": "Fresh-pass-123!"},
        content_type="application/json",
        **auth_headers_for(non_member),
    )
    assert response.status_code == 403
    assert_error_code(response, Code.Auth.NOT_A_MEMBER)


def test_non_member_gets_no_self_service_link(api_client, non_member):
    response = api_client.post(
        "/api/community/request-login-link/",
        {"phone_number": non_member.phone_number},
        content_type="application/json",
    )
    assert response.json()["delivery"] == "admin"
    assert not MagicLoginToken.objects.filter(user=non_member).exists()
