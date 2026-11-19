"""Tests for user search."""

import pytest
from users.models import MembershipStatus, User


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
                membership_status=MembershipStatus.ACTIVE_MEMBER,
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
        other_user.save(update_fields=other_user.apply_guidelines_pause(by=None))
        response = api_client.get("/api/auth/users/search/?q=Other", **auth_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids

    def test_search_excludes_non_members(self, api_client, auth_headers, other_user):
        other_user.save(
            update_fields=other_user.set_membership_status(MembershipStatus.NONE, by=None)
        )
        response = api_client.get("/api/auth/users/search/?q=Other", **auth_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids
