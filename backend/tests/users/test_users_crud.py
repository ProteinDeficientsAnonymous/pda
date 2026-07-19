"""Tests for user create, bulk create, and search."""

import pytest
from community._validation import Code
from tests._asserts import assert_error_code
from users.models import User
from users.roles import Role


@pytest.mark.django_db
class TestCreateUser:
    def test_create_user_invalid_phone(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "not-a-phone", "first_name": "Test"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Phone.INVALID, "phone_number")

    def test_create_user_with_role_id(self, api_client, manage_users_headers, db):
        role = Role.objects.create(name="custom_role", permissions=[])
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550901", "first_name": "Roled", "role_id": str(role.id)},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 201

    def test_create_user_non_admin_cannot_assign_admin_role(self, api_client, manage_users_headers):
        admin_role = Role.objects.get(name="admin")
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550950", "first_name": "Nope", "role_id": str(admin_role.id)},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, Code.Role.CANNOT_GRANT_ADMIN, "role_id")
        assert not User.objects.filter(phone_number="+12025550950").exists()

    def test_create_user_invalid_role_id(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {
                "phone_number": "+12025550902",
                "first_name": "Badrole",
                "role_id": "00000000-0000-0000-0000-000000000000",
            },
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 404
        assert_error_code(response, Code.Role.NOT_FOUND, "role_id")

    def test_create_user_sets_needs_onboarding(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550903", "first_name": "Onboard"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 201
        user = User.objects.get(phone_number="+12025550903")
        assert user.needs_onboarding is True

    def test_create_user_keeps_contact_visibility_default(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550907", "first_name": "Newmember"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 201
        user = User.objects.get(phone_number="+12025550907")
        assert user.needs_onboarding is True
        assert user.show_phone is True
        assert user.show_email is True

    def test_create_user_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550904"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_create_user_rejects_blank_name(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {
                "phone_number": "+12025550905",
                "first_name": "",
                "last_name": "",
            },
            content_type="application/json",
            **manage_users_headers,
        )
        assert_error_code(response, Code.DisplayName.REQUIRED, "first_name")
        assert not User.objects.filter(phone_number="+12025550905").exists()

    def test_create_user_rejects_omitted_name(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550906"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert_error_code(response, Code.DisplayName.REQUIRED, "first_name")
        assert not User.objects.filter(phone_number="+12025550906").exists()

    def test_create_user_rejects_whitespace_only_name(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550908", "first_name": "   "},
            content_type="application/json",
            **manage_users_headers,
        )
        assert_error_code(response, Code.DisplayName.REQUIRED, "first_name")
        assert not User.objects.filter(phone_number="+12025550908").exists()

    def test_create_user_strips_name_whitespace(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550909", "first_name": "  Jamie  ", "last_name": "  Rivera  "},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 201, response.content
        user = User.objects.get(phone_number="+12025550909")
        assert user.first_name == "Jamie"
        assert user.last_name == "Rivera"


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

    def test_bulk_create_users_keeps_contact_visibility_default(
        self, api_client, manage_users_headers
    ):
        response = api_client.post(
            "/api/auth/bulk-create-users/",
            {"phone_numbers": ["+12025551501"]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 200
        user = User.objects.get(phone_number="+12025551501")
        assert user.needs_onboarding is True
        assert user.show_phone is True
        assert user.show_email is True

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
        assert any(u["full_name"] == "Other User" for u in data)

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
        users = [
            User(
                phone_number=f"+1555001{i:04d}",
                first_name=f"Searchable User {i}",
                is_member=True,
            )
            for i in range(11)
        ]
        for user in users:
            user.set_unusable_password()
        User.objects.bulk_create(users)
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

    def test_search_excludes_non_members(self, api_client, auth_headers, other_user):
        other_user.is_member = False
        other_user.save(update_fields=["is_member"])
        response = api_client.get("/api/auth/users/search/?q=Other", **auth_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids
