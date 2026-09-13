import pytest
from ninja_jwt.tokens import RefreshToken
from users.models import User


@pytest.mark.django_db
class TestProfileRespectsShowVeganniversary:
    def test_redacts_veganniversary_when_user_hid_it(self, api_client, auth_headers):
        other_user = User.objects.create_user(
            phone_number="+12025550877",
            password="hiddenpass123",
            first_name="Quiet",
            last_name="Member",
            veganniversary_month=6,
            veganniversary_day=15,
            veganniversary_year=2019,
            show_veganniversary=False,
        )
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["veganniversary"] is None

    def test_shows_veganniversary_when_user_opted_in(self, api_client, auth_headers):
        other_user = User.objects.create_user(
            phone_number="+12025550878",
            password="visiblepass123",
            first_name="Open",
            last_name="Member",
            veganniversary_month=6,
            veganniversary_day=15,
            veganniversary_year=2019,
            show_veganniversary=True,
        )
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["veganniversary"] == {"month": 6, "day": 15, "year": 2019}

    def test_shows_dayless_veganniversary_when_user_opted_in(self, api_client, auth_headers):
        other_user = User.objects.create_user(
            phone_number="+12025550880",
            password="visiblepass123",
            first_name="Open",
            last_name="Member",
            veganniversary_month=6,
            veganniversary_year=2019,
            show_veganniversary=True,
        )
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["veganniversary"] == {"month": 6, "day": None, "year": 2019}

    def test_self_preview_hides_own_veganniversary(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550879",
            password="hiddenpass123",
            first_name="Quiet",
            last_name="Member",
            veganniversary_month=6,
            veganniversary_day=15,
            veganniversary_year=2019,
            show_veganniversary=False,
        )
        refresh = RefreshToken.for_user(user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.get(f"/api/auth/users/{user.pk}/profile/", **headers)
        assert response.status_code == 200
        assert response.json()["veganniversary"] is None


@pytest.mark.django_db
class TestMeVeganniversaryPrivacy:
    def test_me_always_shows_own_veganniversary(self, api_client, test_user):
        test_user.veganniversary_month = 6
        test_user.veganniversary_day = 15
        test_user.veganniversary_year = 2019
        test_user.show_veganniversary = False
        test_user.save(
            update_fields=[
                "veganniversary_month",
                "veganniversary_day",
                "veganniversary_year",
                "show_veganniversary",
            ]
        )
        refresh = RefreshToken.for_user(test_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.get("/api/auth/me/", **headers)
        assert response.status_code == 200
        assert response.json()["veganniversary"] == {"month": 6, "day": 15, "year": 2019}
        assert response.json()["show_veganniversary"] is False
        assert response.json()["veganniversary_shoutout_opt_in"] is False

    def test_patch_me_persists_privacy_flags(self, api_client, auth_headers, test_user):
        response = api_client.patch(
            "/api/auth/me/",
            {"show_veganniversary": False, "veganniversary_shoutout_opt_in": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["show_veganniversary"] is False
        assert response.json()["veganniversary_shoutout_opt_in"] is True
        test_user.refresh_from_db()
        assert test_user.show_veganniversary is False
        assert test_user.veganniversary_shoutout_opt_in is True

    def test_me_has_seen_veganniversary_defaults_false(self, api_client, test_user):
        refresh = RefreshToken.for_user(test_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.get("/api/auth/me/", **headers)
        assert response.status_code == 200
        assert response.json()["has_seen_veganniversary"] is False

    def test_patch_has_seen_veganniversary(self, api_client, auth_headers, test_user):
        response = api_client.patch(
            "/api/auth/me/",
            {"has_seen_veganniversary": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["has_seen_veganniversary"] is True
        test_user.refresh_from_db()
        assert test_user.has_seen_veganniversary is True
