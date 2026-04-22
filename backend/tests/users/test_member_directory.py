"""Tests for the authed member directory endpoint."""

import pytest
from django.utils import timezone


@pytest.mark.django_db
class TestMemberDirectory:
    def test_requires_auth(self, api_client):
        response = api_client.get("/api/auth/users/directory/")
        assert response.status_code == 401

    def test_authed_caller_sees_directory(self, api_client, auth_headers, other_user):
        response = api_client.get("/api/auth/users/directory/", **auth_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) in ids

    def test_excludes_paused_users(self, api_client, auth_headers, other_user):
        other_user.is_paused = True
        other_user.save(update_fields=["is_paused"])
        response = api_client.get("/api/auth/users/directory/", **auth_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids

    def test_excludes_archived_users(self, api_client, auth_headers, other_user):
        other_user.archived_at = timezone.now()
        other_user.save(update_fields=["archived_at"])
        response = api_client.get("/api/auth/users/directory/", **auth_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids

    def test_excludes_onboarding_pending_users(self, api_client, auth_headers, other_user):
        other_user.needs_onboarding = True
        other_user.save(update_fields=["needs_onboarding"])
        response = api_client.get("/api/auth/users/directory/", **auth_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids

    def test_redacts_phone_when_user_hid_it(self, api_client, auth_headers, other_user):
        other_user.show_phone = False
        other_user.save(update_fields=["show_phone"])
        response = api_client.get("/api/auth/users/directory/", **auth_headers)
        assert response.status_code == 200
        entry = next(u for u in response.json() if u["id"] == str(other_user.pk))
        assert entry["phone_number"] == ""

    def test_redacts_email_when_user_hid_it(self, api_client, auth_headers, other_user):
        other_user.email = "hidden@example.com"
        other_user.show_email = False
        other_user.save(update_fields=["email", "show_email"])
        response = api_client.get("/api/auth/users/directory/", **auth_headers)
        assert response.status_code == 200
        entry = next(u for u in response.json() if u["id"] == str(other_user.pk))
        assert entry["email"] == ""

    def test_shows_phone_when_user_opted_in(self, api_client, auth_headers, other_user):
        response = api_client.get("/api/auth/users/directory/", **auth_headers)
        entry = next(u for u in response.json() if u["id"] == str(other_user.pk))
        assert entry["phone_number"] == other_user.phone_number
