"""Tests for the admin-managed club list."""

import uuid

import pytest
from community.models import Club
from community.validation import Code

from tests._asserts import assert_error_code

URL = "/api/community/clubs/"


def _post(api_client, headers, **body):
    return api_client.post(URL, body, content_type="application/json", **headers)


def _patch(api_client, headers, club_id, **body):
    return api_client.patch(f"{URL}{club_id}/", body, content_type="application/json", **headers)


@pytest.mark.django_db
class TestClubs:
    def test_list_is_public_and_sorted_by_name(self, api_client):
        Club.objects.create(name="movie club")
        Club.objects.create(name="book club", requirements="read along")

        response = api_client.get(URL)

        assert response.status_code == 200
        assert [(c["name"], c["requirements"]) for c in response.json()] == [
            ("book club", "read along"),
            ("movie club", ""),
        ]

    def test_create_trims_name_and_requirements(self, api_client, manage_events_headers):
        response = _post(
            api_client, manage_events_headers, name="  doggie meetup ", requirements=" dog parents "
        )

        assert response.status_code == 201
        club = Club.objects.get()
        assert (club.name, club.requirements) == ("doggie meetup", "dog parents")
        assert response.json()["id"] == str(club.id)

    def test_create_rejects_blank_name(self, api_client, manage_events_headers):
        response = _post(api_client, manage_events_headers, name="   ")

        assert response.status_code == 422
        assert_error_code(response, Code.Club.NAME_REQUIRED)

    def test_create_rejects_duplicate_name_ignoring_case(self, api_client, manage_events_headers):
        Club.objects.create(name="Book Club")

        response = _post(api_client, manage_events_headers, name="book club")

        assert response.status_code == 422
        assert_error_code(response, Code.Club.NAME_ALREADY_EXISTS)

    def test_update_renames(self, api_client, manage_events_headers):
        club = Club.objects.create(name="book club")

        response = _patch(
            api_client, manage_events_headers, club.id, name="books", requirements="monthly"
        )

        assert response.status_code == 200
        club.refresh_from_db()
        assert (club.name, club.requirements) == ("books", "monthly")

    def test_update_keeps_own_name(self, api_client, manage_events_headers):
        club = Club.objects.create(name="book club")

        response = _patch(api_client, manage_events_headers, club.id, name="Book Club")

        assert response.status_code == 200
        club.refresh_from_db()
        assert club.name == "Book Club"

    def test_update_rejects_another_clubs_name(self, api_client, manage_events_headers):
        Club.objects.create(name="movie club")
        club = Club.objects.create(name="book club")

        response = _patch(api_client, manage_events_headers, club.id, name="Movie Club")

        assert response.status_code == 422
        assert_error_code(response, Code.Club.NAME_ALREADY_EXISTS)

    def test_delete(self, api_client, manage_events_headers):
        club = Club.objects.create(name="book club")

        response = api_client.delete(f"{URL}{club.id}/", **manage_events_headers)

        assert response.status_code == 204
        assert not Club.objects.exists()

    def test_unknown_club(self, api_client, manage_events_headers):
        response = _patch(api_client, manage_events_headers, uuid.uuid4(), name="x")

        assert response.status_code == 404
        assert_error_code(response, Code.Club.NOT_FOUND)

    def test_writes_require_manage_events(self, api_client, auth_headers):
        club = Club.objects.create(name="book club")

        responses = [
            _post(api_client, auth_headers, name="movie club"),
            _patch(api_client, auth_headers, club.id, name="books"),
            api_client.delete(f"{URL}{club.id}/", **auth_headers),
        ]

        for response in responses:
            assert response.status_code == 403
            assert_error_code(response, Code.Perm.DENIED)
        assert Club.objects.get().name == "book club"
