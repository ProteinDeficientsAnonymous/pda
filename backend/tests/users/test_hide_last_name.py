import pytest
from users.models import User
from users.roles import Role


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        phone_number="+12025550501",
        password="adminpass123",
        first_name="Admin",
        last_name="Adminson",
    )
    admin_role = Role.objects.get(name="admin", is_default=True)
    user.roles.add(admin_role)
    return user


@pytest.fixture
def admin_headers(admin_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(admin_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def hidden_user(db):
    return User.objects.create_user(
        phone_number="+12025550502",
        password="hiddenpass123",
        first_name="Hidden",
        last_name="Lastname",
        hide_last_name=True,
    )


@pytest.mark.django_db
class TestDirectoryHidesLastName:
    def test_non_admin_sees_first_name_only(self, api_client, auth_headers, hidden_user):
        response = api_client.get("/api/auth/users/directory/", **auth_headers)
        assert response.status_code == 200
        entry = next(u for u in response.json() if u["id"] == str(hidden_user.pk))
        assert entry["last_name"] == ""
        assert entry["full_name"] == "Hidden"

    def test_admin_sees_full_name(self, api_client, admin_headers, hidden_user):
        response = api_client.get("/api/auth/users/directory/", **admin_headers)
        assert response.status_code == 200
        entry = next(u for u in response.json() if u["id"] == str(hidden_user.pk))
        assert entry["last_name"] == "Lastname"
        assert entry["full_name"] == "Hidden Lastname"


@pytest.mark.django_db
class TestProfileHidesLastName:
    def test_non_admin_sees_first_name_only(self, api_client, auth_headers, hidden_user):
        response = api_client.get(f"/api/auth/users/{hidden_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["last_name"] == ""
        assert body["full_name"] == "Hidden"

    def test_admin_sees_full_name(self, api_client, admin_headers, hidden_user):
        response = api_client.get(f"/api/auth/users/{hidden_user.pk}/profile/", **admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["last_name"] == "Lastname"
        assert body["full_name"] == "Hidden Lastname"

    def test_self_sees_own_full_name(self, api_client, hidden_user):
        from ninja_jwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(hidden_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.get(f"/api/auth/users/{hidden_user.pk}/profile/", **headers)
        assert response.status_code == 200
        body = response.json()
        assert body["last_name"] == "Lastname"
        assert body["full_name"] == "Hidden Lastname"


@pytest.mark.django_db
class TestSearchHidesLastName:
    def test_non_admin_search_by_hidden_last_name_no_match(
        self, api_client, auth_headers, hidden_user
    ):
        response = api_client.get("/api/auth/users/search/?q=Lastname", **auth_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(hidden_user.pk) not in ids

    def test_non_admin_search_by_first_name_matches_but_omits_last_name(
        self, api_client, auth_headers, hidden_user
    ):
        response = api_client.get("/api/auth/users/search/?q=Hidden", **auth_headers)
        assert response.status_code == 200
        entry = next(u for u in response.json() if u["id"] == str(hidden_user.pk))
        assert entry["last_name"] == ""
        assert entry["full_name"] == "Hidden"

    def test_admin_search_by_last_name_matches_with_full_name(
        self, api_client, admin_headers, hidden_user
    ):
        response = api_client.get("/api/auth/users/search/?q=Lastname", **admin_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(hidden_user.pk) in ids
        entry = next(u for u in response.json() if u["id"] == str(hidden_user.pk))
        assert entry["last_name"] == "Lastname"
        assert entry["full_name"] == "Hidden Lastname"


@pytest.mark.django_db
class TestMeHideLastName:
    def test_me_always_shows_own_last_name(self, api_client, hidden_user):
        from ninja_jwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(hidden_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.get("/api/auth/me/", **headers)
        assert response.status_code == 200
        body = response.json()
        assert body["last_name"] == "Lastname"
        assert body["full_name"] == "Hidden Lastname"
        assert body["hide_last_name"] is True

    def test_patch_me_persists_hide_last_name(self, api_client, auth_headers, test_user):
        response = api_client.patch(
            "/api/auth/me/",
            {"hide_last_name": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["hide_last_name"] is True
        test_user.refresh_from_db()
        assert test_user.hide_last_name is True
