"""Tests for PATCH /api/auth/me/ (update profile)."""

from datetime import date

import pytest
from users.models import User


@pytest.mark.django_db
class TestUpdateMe:
    def test_update_me_invalid_email_rejected(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"email": "notanemail"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422

    def test_update_me_valid_email_accepted(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"email": "valid@example.com"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["email"] == "valid@example.com"

    def test_update_me_empty_email_accepted(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"email": ""},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200

    def test_update_week_start_to_monday(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"week_start": "monday"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["week_start"] == "monday"

    def test_update_week_start_invalid_value_rejected(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"week_start": "wednesday"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422

    def test_update_pronouns_accepted(self, api_client, auth_headers, test_user):
        response = api_client.patch(
            "/api/auth/me/",
            {"pronouns": "  they/them  "},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["pronouns"] == "they/them"
        test_user.refresh_from_db()
        assert test_user.pronouns == "they/them"

    def test_update_pronouns_can_be_cleared(self, api_client, auth_headers, test_user):
        test_user.pronouns = "she/her"
        test_user.save(update_fields=["pronouns"])
        response = api_client.patch(
            "/api/auth/me/",
            {"pronouns": ""},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["pronouns"] == ""

    def test_update_pronouns_too_long_rejected(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"pronouns": "x" * 101},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422


@pytest.mark.django_db
class TestUpdateBirthday:
    def test_set_birthday_accepted(self, api_client, auth_headers, test_user):
        response = api_client.patch(
            "/api/auth/me/",
            {"birthday": "1990-06-15"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["birthday"] == "1990-06-15"
        test_user.refresh_from_db()
        assert test_user.birthday.isoformat() == "1990-06-15"

    def test_birthday_can_be_cleared(self, api_client, auth_headers, test_user):
        test_user.birthday = date(1990, 6, 15)
        test_user.save(update_fields=["birthday"])
        response = api_client.patch(
            "/api/auth/me/",
            {"birthday": ""},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["birthday"] is None
        test_user.refresh_from_db()
        assert test_user.birthday is None

    def test_birthday_omitted_leaves_value_untouched(self, api_client, auth_headers, test_user):
        test_user.birthday = date(1990, 6, 15)
        test_user.save(update_fields=["birthday"])
        response = api_client.patch(
            "/api/auth/me/",
            {"pronouns": "they/them"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        test_user.refresh_from_db()
        assert test_user.birthday == date(1990, 6, 15)

    def test_malformed_birthday_rejected(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"birthday": "not-a-date"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422


@pytest.mark.django_db
class TestPatchMeEmail:
    def test_update_email_lowercases(self, api_client, auth_headers, test_user):
        resp = api_client.patch(
            "/api/auth/me/",
            data={"email": "FOO@Example.com"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
        test_user.refresh_from_db()
        assert test_user.email == "foo@example.com"

    def test_duplicate_email_rejected(self, api_client, auth_headers, db):
        User.objects.create_user(
            phone_number="+12025550199", first_name="other", last_name="", email="taken@example.com"
        )
        resp = api_client.patch(
            "/api/auth/me/",
            data={"email": "taken@example.com"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["detail"][0]["code"] == "email.already_exists"

    def test_duplicate_email_case_insensitive(self, api_client, auth_headers, db):
        User.objects.create_user(
            phone_number="+12025550199", first_name="other", last_name="", email="taken@example.com"
        )
        resp = api_client.patch(
            "/api/auth/me/",
            data={"email": "Taken@Example.com"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "email.already_exists"
