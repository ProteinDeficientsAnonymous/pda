import pytest
from community.models import JoinRequestStatus
from community.validation import Code
from django.utils import timezone
from users.models import MagicLoginToken, MembershipStatus

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for

pytestmark = pytest.mark.django_db

PASSWORD = "Sprout-pass-123!"


@pytest.fixture
def rejected_user(api_client, vettor_headers, sample_join_request):
    for status in (JoinRequestStatus.TENTATIVE, JoinRequestStatus.REJECTED):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": status},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
    sample_join_request.refresh_from_db()
    user = sample_join_request.user
    user.set_password(PASSWORD)
    user.needs_onboarding = False
    user.guidelines_consent_at = timezone.now()
    user.save(update_fields=["password", "needs_onboarding", "guidelines_consent_at"])
    assert user.membership_status == MembershipStatus.REJECTED
    return user


def test_password_login_is_blocked(api_client, rejected_user):
    response = api_client.post(
        "/api/auth/login/",
        {"phone_number": rejected_user.phone_number, "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 403
    assert_error_code(response, Code.Auth.ACCOUNT_REJECTED)


def test_magic_login_is_blocked(api_client, rejected_user):
    magic = MagicLoginToken.create_for_user(rejected_user)
    response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
    assert response.status_code == 403
    assert_error_code(response, Code.Auth.ACCOUNT_REJECTED)


def test_existing_session_is_blocked(api_client, rejected_user):
    response = api_client.get("/api/auth/me/", **auth_headers_for(rejected_user))
    assert response.status_code == 403
    assert_error_code(response, Code.Auth.ACCOUNT_REJECTED)
