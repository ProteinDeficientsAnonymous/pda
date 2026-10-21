import pytest
from community.models import MemberPromotionEmailTemplate
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code


@pytest.fixture
def edit_promotion_email_user(db):
    user = User.objects.create_user(
        phone_number="+15550003004",
        password="vetterpass123",
        first_name="Vetter",
        last_name="Four",
    )
    role = Role.objects.create(
        name="promotion_email_editor", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS]
    )
    user.roles.add(role)
    return user


@pytest.fixture
def edit_promotion_email_headers(edit_promotion_email_user):
    refresh = RefreshToken.for_user(edit_promotion_email_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestGetMemberPromotionEmail:
    def test_authenticated_user_sees_default_empty_body(self, api_client, auth_headers):
        response = api_client.get("/api/community/member-promotion-email/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["body"] == ""
        assert "updated_at" in data

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get("/api/community/member-promotion-email/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestUpdateMemberPromotionEmail:
    def test_with_permission_updates_body(self, api_client, edit_promotion_email_headers):
        response = api_client.patch(
            "/api/community/member-promotion-email/",
            data={"body": "hi ${FIRST_NAME}, join us at ${WHATSAPP_LINK}"},
            content_type="application/json",
            **edit_promotion_email_headers,
        )
        assert response.status_code == 200
        assert "${WHATSAPP_LINK}" in response.json()["body"]
        assert (
            MemberPromotionEmailTemplate.get().body
            == "hi ${FIRST_NAME}, join us at ${WHATSAPP_LINK}"
        )

    def test_without_permission_returns_403(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/community/member-promotion-email/",
            data={"body": "sneaky edit"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, "perm.denied")

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.patch(
            "/api/community/member-promotion-email/",
            data={"body": "sneaky edit"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_empty_body_rejected(self, api_client, edit_promotion_email_headers):
        response = api_client.patch(
            "/api/community/member-promotion-email/",
            data={"body": "   "},
            content_type="application/json",
            **edit_promotion_email_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, "member_promotion_email.body_required", expected_field="body")

    def test_too_long_body_rejected(self, api_client, edit_promotion_email_headers):
        response = api_client.patch(
            "/api/community/member-promotion-email/",
            data={"body": "x" * 5000},
            content_type="application/json",
            **edit_promotion_email_headers,
        )
        assert response.status_code == 422
        entry = assert_error_code(
            response, "member_promotion_email.body_too_long", expected_field="body"
        )
        assert entry["params"]["max_length"] == 4000

    def test_does_not_touch_the_sms_promotion_message(
        self, api_client, edit_promotion_email_headers
    ):
        from community.models import MemberPromotionMessageTemplate

        api_client.patch(
            "/api/community/member-promotion-email/",
            data={"body": "email copy"},
            content_type="application/json",
            **edit_promotion_email_headers,
        )
        assert MemberPromotionMessageTemplate.get().body == ""
