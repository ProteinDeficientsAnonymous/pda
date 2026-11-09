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
def rejected_user(db):
    return make_user(
        password=PASSWORD,
        membership_status=MembershipStatus.REJECTED,
        guidelines_consent_at=timezone.now(),
    )


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
