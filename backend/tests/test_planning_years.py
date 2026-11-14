import pytest
from community.models import PlanningSlot, PlanningYear, SlotAssignment
from community.planning.years import get_year_or_404
from community.validation import Code, ValidationException
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._events import make_event
from tests._users import make_user

BASE = "/api/community/planning"
VIEW = PermissionKey.VIEW_EVENT_PLANNING
MANAGE = PermissionKey.MANAGE_EVENT_PLANNING
NO_SLOT = "00000000-0000-0000-0000-000000000000"
NEW_SLOT = {"label": "extra walk", "month": 5, "kind": "monthly"}

VIEW_ROUTES = [
    ("get", f"{BASE}/years/", None),
    ("get", f"{BASE}/years/2027/slots/", None),
]
MANAGE_ROUTES = [
    ("post", f"{BASE}/years/", {"year": 2028}),
    ("post", f"{BASE}/years/2027/slots/", NEW_SLOT),
    ("patch", f"{BASE}/slots/{NO_SLOT}/", {"label": "x"}),
    ("delete", f"{BASE}/slots/{NO_SLOT}/", None),
]


def send(api_client, method, url, body=None, headers=None):
    kwargs = {"data": body, "content_type": "application/json"} if body is not None else {}
    return getattr(api_client, method)(url, **kwargs, **(headers or {}))


def headers_for(*permissions):
    return auth_headers_for(make_user(*permissions))


@pytest.fixture
def year(db):
    return PlanningYear.create_with_default_slots(2027)


@pytest.mark.django_db
class TestAccess:
    @pytest.mark.parametrize(("method", "url", "body"), VIEW_ROUTES + MANAGE_ROUTES)
    def test_unauthenticated(self, api_client, method, url, body):
        assert send(api_client, method, url, body).status_code == 401

    @pytest.mark.parametrize(("method", "url", "body"), VIEW_ROUTES + MANAGE_ROUTES)
    def test_plain_member_forbidden(self, api_client, method, url, body):
        assert send(api_client, method, url, body, headers_for()).status_code == 403

    @pytest.mark.parametrize(("method", "url", "body"), MANAGE_ROUTES)
    def test_view_only_forbidden_on_manage_routes(self, api_client, method, url, body):
        assert send(api_client, method, url, body, headers_for(VIEW)).status_code == 403


@pytest.mark.django_db
class TestYears:
    def test_list_years(self, api_client, year):
        response = send(api_client, "get", f"{BASE}/years/", headers=headers_for(VIEW))
        assert response.status_code == 200
        assert [y["year"] for y in response.json()] == [2027]

    def test_create_year_seeds_default_slots(self, api_client):
        response = send(api_client, "post", f"{BASE}/years/", {"year": 2028}, headers_for(MANAGE))
        assert response.status_code == 201
        assert response.json()["year"] == 2028
        assert PlanningSlot.objects.filter(planning_year__year=2028).count() == 14

    def test_create_duplicate_year(self, api_client, year):
        response = send(api_client, "post", f"{BASE}/years/", {"year": 2027}, headers_for(MANAGE))
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.YEAR_EXISTS, "year")

    def test_create_year_out_of_range(self, api_client):
        response = send(api_client, "post", f"{BASE}/years/", {"year": 1999}, headers_for(MANAGE))
        assert response.status_code == 422

    def test_get_year_or_404(self, year):
        assert get_year_or_404(2027) == year
        with pytest.raises(ValidationException) as exc:
            get_year_or_404(2099)
        assert exc.value.code == Code.Planning.YEAR_NOT_FOUND
        assert exc.value.status_code == 404


@pytest.mark.django_db
class TestSlots:
    def test_list_slots(self, api_client, year):
        response = send(api_client, "get", f"{BASE}/years/2027/slots/", headers=headers_for(VIEW))
        assert response.status_code == 200
        slots = response.json()
        assert [s["label"] for s in slots][:2] == ["january", "february"]
        assert len(slots) == 14
        assert slots[0]["event_id"] is slots[0]["event_slug"] is slots[0]["event_status"] is None

    def test_list_slots_includes_linked_event(self, api_client, year):
        event = make_event()
        year.slots.filter(label="march").update(event=event)
        slots = send(
            api_client, "get", f"{BASE}/years/2027/slots/", headers=headers_for(VIEW)
        ).json()
        march = next(s for s in slots if s["label"] == "march")
        assert march["event_id"] == str(event.id)
        assert march["event_slug"] == event.slug
        assert march["event_status"] == event.status

    @pytest.mark.parametrize(
        ("method", "body", "perm"),
        [("get", None, VIEW), ("post", NEW_SLOT, MANAGE)],
    )
    def test_unknown_year(self, api_client, method, body, perm):
        response = send(api_client, method, f"{BASE}/years/2099/slots/", body, headers_for(perm))
        assert response.status_code == 404
        assert_error_code(response, Code.Planning.YEAR_NOT_FOUND)

    def test_create_slot_appends_order(self, api_client, year):
        response = send(
            api_client, "post", f"{BASE}/years/2027/slots/", NEW_SLOT, headers_for(MANAGE)
        )
        assert response.status_code == 201
        assert (response.json()["label"], response.json()["order"]) == ("extra walk", 15)

    def test_create_slot_invalid_month(self, api_client, year):
        response = send(
            api_client,
            "post",
            f"{BASE}/years/2027/slots/",
            {**NEW_SLOT, "month": 13},
            headers_for(MANAGE),
        )
        assert response.status_code == 422

    def test_patch_slot_updates_only_sent_fields(self, api_client, year):
        slot = year.slots.get(label="march")
        response = send(
            api_client,
            "patch",
            f"{BASE}/slots/{slot.id}/",
            {"label": "march walk"},
            headers_for(MANAGE),
        )
        assert response.status_code == 200
        slot.refresh_from_db()
        assert (slot.label, slot.month) == ("march walk", 3)

    def test_slot_not_found(self, api_client, year):
        for method, body in (("patch", {"label": "x"}), ("delete", None)):
            response = send(
                api_client, method, f"{BASE}/slots/{NO_SLOT}/", body, headers_for(MANAGE)
            )
            assert response.status_code == 404
            assert_error_code(response, Code.Planning.SLOT_NOT_FOUND)

    def test_delete_slot_cascades_assignments(self, api_client, year):
        slot = year.slots.first()
        SlotAssignment.objects.create(slot=slot, user=make_user())
        response = send(
            api_client, "delete", f"{BASE}/slots/{slot.id}/", headers=headers_for(MANAGE)
        )
        assert response.status_code == 204
        assert not PlanningSlot.objects.filter(id=slot.id).exists()
        assert not SlotAssignment.objects.exists()
