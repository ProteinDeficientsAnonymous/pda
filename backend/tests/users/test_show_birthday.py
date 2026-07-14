import pytest
from ninja_jwt.tokens import RefreshToken
from users.models import User


@pytest.mark.django_db
class TestProfileRespectsShowBirthday:
    def test_redacts_birthday_when_user_hid_it(self, api_client, auth_headers):
        other_user = User.objects.create_user(
            phone_number="+12025550777",
            password="hiddenpass123",
            first_name="Quiet",
            last_name="Member",
            birthday_month=6,
            birthday_day=15,
            birthday_year=1990,
            show_birthday=False,
        )
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["birthday"] is None

    def test_shows_birthday_when_user_opted_in(self, api_client, auth_headers):
        other_user = User.objects.create_user(
            phone_number="+12025550778",
            password="visiblepass123",
            first_name="Open",
            last_name="Member",
            birthday_month=6,
            birthday_day=15,
            birthday_year=1990,
            show_birthday=True,
        )
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["birthday"] == {"month": 6, "day": 15, "year": 1990}

    def test_shows_yearless_birthday_when_user_opted_in(self, api_client, auth_headers):
        other_user = User.objects.create_user(
            phone_number="+12025550780",
            password="visiblepass123",
            first_name="Open",
            last_name="Member",
            birthday_month=6,
            birthday_day=15,
            show_birthday=True,
        )
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["birthday"] == {"month": 6, "day": 15, "year": None}

    def test_self_preview_hides_own_birthday(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550779",
            password="hiddenpass123",
            first_name="Quiet",
            last_name="Member",
            birthday_month=6,
            birthday_day=15,
            birthday_year=1990,
            show_birthday=False,
        )
        refresh = RefreshToken.for_user(user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.get(f"/api/auth/users/{user.pk}/profile/", **headers)
        assert response.status_code == 200
        assert response.json()["birthday"] is None


@pytest.mark.django_db
class TestMeShowBirthday:
    def test_me_always_shows_own_birthday(self, api_client, test_user):
        test_user.birthday_month = 6
        test_user.birthday_day = 15
        test_user.birthday_year = 1990
        test_user.show_birthday = False
        test_user.save(
            update_fields=["birthday_month", "birthday_day", "birthday_year", "show_birthday"]
        )
        refresh = RefreshToken.for_user(test_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.get("/api/auth/me/", **headers)
        assert response.status_code == 200
        assert response.json()["birthday"] == {"month": 6, "day": 15, "year": 1990}
        assert response.json()["show_birthday"] is False

    def test_patch_me_persists_show_birthday(self, api_client, auth_headers, test_user):
        response = api_client.patch(
            "/api/auth/me/",
            {"show_birthday": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["show_birthday"] is False
        test_user.refresh_from_db()
        assert test_user.show_birthday is False
