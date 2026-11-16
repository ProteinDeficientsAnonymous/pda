from datetime import date
from decimal import Decimal

import pytest
from community.models import ReserveEntry
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._users import make_user

URL = "/api/community/reserve/entries/"


@pytest.fixture
def editor_headers(db):
    return auth_headers_for(make_user(PermissionKey.EDIT_GUIDELINES))


@pytest.fixture
def member_headers(db):
    return auth_headers_for(make_user())


@pytest.fixture
def entry(db):
    return ReserveEntry.objects.create(
        label="peacefood walk", occurred_on=date(2026, 9, 12), collected=Decimal("315.00")
    )


@pytest.mark.django_db
class TestCreateReserveEntry:
    def test_create_reserve_entry(self, api_client, editor_headers):
        payload = {
            "label": "stickers",
            "kind": "cost",
            "occurred_on": "2026-11-15",
            "paid_out": "103.65",
        }

        response = api_client.post(URL, payload, content_type="application/json", **editor_headers)

        assert response.status_code == 201
        assert response.json()["left_over"] == "-103.65"
        assert response.json()["kind"] == "cost"
        assert ReserveEntry.objects.get().label == "stickers"

    def test_create_reserve_entry_rejects_negative(self, api_client, editor_headers):
        payload = {"label": "x", "occurred_on": "2026-11-15", "paid_out": "-1"}

        response = api_client.post(URL, payload, content_type="application/json", **editor_headers)

        assert response.status_code == 422
        assert not ReserveEntry.objects.exists()

    def test_create_reserve_entry_requires_permission(self, api_client, member_headers):
        payload = {"label": "x", "occurred_on": "2026-11-15"}

        response = api_client.post(URL, payload, content_type="application/json", **member_headers)

        assert response.status_code == 403


@pytest.mark.django_db
class TestUpdateReserveEntry:
    def test_update_reserve_entry_partial(self, api_client, editor_headers, entry):
        response = api_client.patch(
            f"{URL}{entry.id}/",
            {"paid_out": "288.68"},
            content_type="application/json",
            **editor_headers,
        )

        assert response.status_code == 200
        assert response.json()["left_over"] == "26.32"
        entry.refresh_from_db()
        assert entry.label == "peacefood walk"

    def test_update_reserve_entry_not_found(self, api_client, editor_headers):
        response = api_client.patch(
            f"{URL}00000000-0000-0000-0000-000000000000/",
            {"paid_out": "1"},
            content_type="application/json",
            **editor_headers,
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestDeleteReserveEntry:
    def test_delete_reserve_entry(self, api_client, editor_headers, entry):
        response = api_client.delete(f"{URL}{entry.id}/", **editor_headers)

        assert response.status_code == 204
        assert not ReserveEntry.objects.exists()

    def test_delete_reserve_entry_requires_permission(self, api_client, member_headers, entry):
        response = api_client.delete(f"{URL}{entry.id}/", **member_headers)

        assert response.status_code == 403
        assert ReserveEntry.objects.exists()
