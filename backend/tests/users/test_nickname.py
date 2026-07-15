import pytest


@pytest.mark.django_db
class TestUpdateMeNickname:
    def test_update_nickname_accepted(self, api_client, auth_headers, test_user):
        response = api_client.patch(
            "/api/auth/me/",
            {"nickname": "  Lee  "},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["nickname"] == "Lee"
        test_user.refresh_from_db()
        assert test_user.nickname == "Lee"

    def test_update_nickname_can_be_cleared(self, api_client, auth_headers, test_user):
        test_user.nickname = "Lee"
        test_user.save(update_fields=["nickname"])
        response = api_client.patch(
            "/api/auth/me/",
            {"nickname": ""},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["nickname"] == ""

    def test_update_nickname_too_long_rejected(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"nickname": "x" * 65},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422

    def test_nickname_absent_by_default(self, api_client, auth_headers):
        response = api_client.get("/api/auth/me/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["nickname"] == ""


@pytest.mark.django_db
class TestMemberProfileNickname:
    def test_member_profile_returns_nickname(self, api_client, auth_headers, other_user):
        other_user.nickname = "Birdie"
        other_user.save(update_fields=["nickname"])
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["nickname"] == "Birdie"

    def test_member_profile_nickname_blank_by_default(self, api_client, auth_headers, other_user):
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["nickname"] == ""
