import pytest
from community.models import BiannualInterest, PlanningAvailability, PlanningYear
from community.validation import Code
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._planning import headers_for, send
from tests._users import make_user

URL = "/api/community/planning/years/2027/availability/me/"
VIEW = PermissionKey.VIEW_EVENT_PLANNING


def body(slots, interest="yes", count=2):
    return {
        "slot_ids": [str(s.id) for s in slots],
        "biannual_interest": interest,
        "monthly_count": count,
    }


@pytest.mark.django_db
class TestAccess:
    @pytest.mark.parametrize("method", ["get", "put"])
    def test_unauthenticated(self, api_client, year, method):
        assert send(api_client, method, URL, body([])).status_code == 401

    @pytest.mark.parametrize("method", ["get", "put"])
    def test_plain_member_forbidden(self, api_client, year, method):
        assert send(api_client, method, URL, body([]), headers_for()).status_code == 403

    @pytest.mark.parametrize("method", ["get", "put"])
    def test_unknown_year(self, api_client, method):
        response = send(api_client, method, URL, body([]), headers_for(VIEW))
        assert response.status_code == 404
        assert_error_code(response, Code.Planning.YEAR_NOT_FOUND)


@pytest.mark.django_db
class TestAvailability:
    def test_get_default_when_not_submitted(self, api_client, year):
        response = send(api_client, "get", URL, headers=headers_for(VIEW))
        assert response.status_code == 200
        assert response.json() == {
            "submitted": False,
            "biannual_interest": None,
            "monthly_count": 0,
            "slot_ids": [],
            "updated_at": None,
        }

    def test_put_creates_then_replaces_slots(self, api_client, year):
        user = make_user(VIEW)
        headers = auth_headers_for(user)
        slots = list(year.slots.all()[:3])

        created = send(api_client, "put", URL, body(slots[:2]), headers)
        assert created.status_code == 200
        assert created.json()["submitted"] is True
        assert sorted(created.json()["slot_ids"]) == sorted(str(s.id) for s in slots[:2])

        replaced = send(api_client, "put", URL, body(slots[2:], "maybe", 5), headers)
        assert replaced.json()["slot_ids"] == [str(slots[2].id)]
        assert replaced.json()["biannual_interest"] == "maybe"
        assert replaced.json()["monthly_count"] == 5

        row = PlanningAvailability.objects.get(planning_year=year, user=user)
        assert row.biannual_interest == BiannualInterest.MAYBE
        assert list(row.available_slots.all()) == [slots[2]]
        assert send(api_client, "get", URL, headers=headers).json() == replaced.json()

    def test_put_empty_slots_clears(self, api_client, year):
        headers = auth_headers_for(make_user(VIEW))
        send(api_client, "put", URL, body(list(year.slots.all()[:2])), headers)
        assert send(api_client, "put", URL, body([]), headers).json()["slot_ids"] == []

    def test_availability_is_per_user(self, api_client, year):
        send(api_client, "put", URL, body(list(year.slots.all()[:1])), headers_for(VIEW))
        assert send(api_client, "get", URL, headers=headers_for(VIEW)).json()["submitted"] is False

    def test_rejects_slot_from_other_year(self, api_client, year):
        other = PlanningYear.create_with_default_slots(2028)
        headers = auth_headers_for(make_user(VIEW))
        response = send(
            api_client, "put", URL, body([year.slots.first(), other.slots.first()]), headers
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.SLOT_NOT_IN_YEAR, "slot_ids")
        assert not PlanningAvailability.objects.exists()

    @pytest.mark.parametrize(
        "payload",
        [
            {"slot_ids": [], "biannual_interest": "yes", "monthly_count": 13},
            {"slot_ids": [], "biannual_interest": "sometimes", "monthly_count": 1},
        ],
    )
    def test_rejects_invalid_payload(self, api_client, year, payload):
        assert send(api_client, "put", URL, payload, headers_for(VIEW)).status_code == 422
