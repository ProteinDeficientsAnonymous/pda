"""Tests for user create, bulk create, and search."""

import pytest
from community._validation import Code
from tests._asserts import assert_error_code
from users.roles import Role


@pytest.mark.django_db
class TestCreateUser:
    def test_create_user_invalid_phone(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "not-a-phone"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Phone.INVALID, "phone_number")

    def test_create_user_with_role_id(self, api_client, manage_users_headers, db):
        role = Role.objects.create(name="custom_role", permissions=[])
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550901", "role_id": str(role.id)},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 201

    def test_create_user_invalid_role_id(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {
                "phone_number": "+12025550902",
                "role_id": "00000000-0000-0000-0000-000000000000",
            },
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 404
        assert_error_code(response, Code.Role.NOT_FOUND, "role_id")

    def test_create_user_sets_needs_onboarding(self, api_client, manage_users_headers):
        from users.models import User

        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550903"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 201
        user = User.objects.get(phone_number="+12025550903")
        assert user.needs_onboarding is True

    def test_create_user_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550904"},
            content_type="application/json",
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestBulkCreateUsers:
    def test_bulk_create_users_success(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/bulk-create-users/",
            {"phone_numbers": ["+12025551001", "+12025551002", "+12025551003"]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 3
        assert data["failed"] == 0
        assert all(r["success"] for r in data["results"])
        assert all(len(r["magic_link_token"]) == 36 for r in data["results"] if r["success"])

    def test_bulk_create_users_requires_permission(self, api_client, auth_headers):
        response = api_client.post(
            "/api/auth/bulk-create-users/",
            {"phone_numbers": ["+12025551101"]},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_bulk_create_users_requires_auth(self, api_client):
        response = api_client.post(
            "/api/auth/bulk-create-users/",
            {"phone_numbers": ["+12025551101"]},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_bulk_create_users_invalid_phone(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/bulk-create-users/",
            {"phone_numbers": ["+12025551201", "not-a-phone"]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 1
        assert data["failed"] == 1
        failed = [r for r in data["results"] if not r["success"]]
        assert failed[0]["phone_number"] == "not-a-phone"
        assert failed[0]["error"] == Code.Phone.INVALID

    def test_bulk_create_users_duplicate_phone(self, api_client, manage_users_headers, test_user):
        response = api_client.post(
            "/api/auth/bulk-create-users/",
            {"phone_numbers": [test_user.phone_number, "+12025551301"]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 1
        assert data["failed"] == 1
        failed = [r for r in data["results"] if not r["success"]]
        assert failed[0]["error"] == Code.Phone.ALREADY_EXISTS

    def test_bulk_create_users_shared_temp_password(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/bulk-create-users/",
            {"phone_numbers": ["+12025551401", "+12025551402"]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 2
        assert all(r.get("magic_link_token") for r in data["results"] if r["success"])

    def test_bulk_create_users_empty_list(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/bulk-create-users/",
            {"phone_numbers": []},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 0
        assert data["failed"] == 0


@pytest.mark.django_db
class TestSearchUsers:
    def test_search_returns_results(self, api_client, auth_headers, other_user):
        response = api_client.get(
            "/api/auth/users/search/?q=Other",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert any(u["display_name"] == "Other User" for u in data)

    def test_search_excludes_self(self, api_client, auth_headers, test_user):
        response = api_client.get(
            "/api/auth/users/search/?q=Test",
            **auth_headers,
        )
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(test_user.pk) not in ids

    def test_search_empty_query_returns_all_others(self, api_client, auth_headers, other_user):
        response = api_client.get("/api/auth/users/search/", **auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_search_requires_auth(self, api_client):
        response = api_client.get("/api/auth/users/search/?q=test")
        assert response.status_code == 401

    def test_search_limits_to_ten_results(self, api_client, auth_headers, db):
        from users.models import User

        for i in range(15):
            User.objects.create_user(
                phone_number=f"+1555001{i:04d}",
                password="pass",
                display_name=f"Searchable User {i}",
            )
        response = api_client.get("/api/auth/users/search/?q=Searchable", **auth_headers)
        assert response.status_code == 200
        assert len(response.json()) <= 10

    def test_search_excludes_paused_users(self, api_client, auth_headers, other_user):
        other_user.is_paused = True
        other_user.save(update_fields=["is_paused"])
        response = api_client.get("/api/auth/users/search/?q=Other", **auth_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids
