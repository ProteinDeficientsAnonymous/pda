import pytest
from ninja_jwt.tokens import RefreshToken
from users.models import User


@pytest.mark.django_db
class TestProfileRespectsShowVeganversary:
    def test_redacts_veganversary_when_user_hid_it(self, api_client, auth_headers):
        other_user = User.objects.create_user(
            phone_number="+12025550877",
            password="hiddenpass123",
            first_name="Quiet",
            last_name="Member",
            veganversary_month=6,
            veganversary_day=15,
            veganversary_year=2019,
            show_veganversary=False,
        )
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["veganversary"] is None

    def test_shows_veganversary_when_user_opted_in(self, api_client, auth_headers):
        other_user = User.objects.create_user(
            phone_number="+12025550878",
            password="visiblepass123",
            first_name="Open",
            last_name="Member",
            veganversary_month=6,
            veganversary_day=15,
            veganversary_year=2019,
            show_veganversary=True,
        )
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["veganversary"] == {"month": 6, "day": 15, "year": 2019}

    def test_shows_dayless_veganversary_when_user_opted_in(self, api_client, auth_headers):
        other_user = User.objects.create_user(
            phone_number="+12025550880",
            password="visiblepass123",
            first_name="Open",
            last_name="Member",
            veganversary_month=6,
            veganversary_year=2019,
            show_veganversary=True,
        )
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["veganversary"] == {"month": 6, "day": None, "year": 2019}

    def test_self_preview_hides_own_veganversary(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550879",
            password="hiddenpass123",
            first_name="Quiet",
            last_name="Member",
            veganversary_month=6,
            veganversary_day=15,
            veganversary_year=2019,
            show_veganversary=False,
        )
        refresh = RefreshToken.for_user(user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.get(f"/api/auth/users/{user.pk}/profile/", **headers)
        assert response.status_code == 200
        assert response.json()["veganversary"] is None


@pytest.mark.django_db
class TestMeVeganversaryPrivacy:
    def test_me_always_shows_own_veganversary(self, api_client, test_user):
        test_user.veganversary_month = 6
        test_user.veganversary_day = 15
        test_user.veganversary_year = 2019
        test_user.show_veganversary = False
        test_user.save(
            update_fields=[
                "veganversary_month",
                "veganversary_day",
                "veganversary_year",
                "show_veganversary",
            ]
        )
        refresh = RefreshToken.for_user(test_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.get("/api/auth/me/", **headers)
        assert response.status_code == 200
        assert response.json()["veganversary"] == {"month": 6, "day": 15, "year": 2019}
        assert response.json()["show_veganversary"] is False
        assert response.json()["veganversary_shoutout_opt_out"] is False

    def test_patch_me_persists_privacy_flags(self, api_client, auth_headers, test_user):
        response = api_client.patch(
            "/api/auth/me/",
            {"show_veganversary": False, "veganversary_shoutout_opt_out": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["show_veganversary"] is False
        assert response.json()["veganversary_shoutout_opt_out"] is True
        test_user.refresh_from_db()
        assert test_user.show_veganversary is False
        assert test_user.veganversary_shoutout_opt_out is True
