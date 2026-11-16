import pytest
from community.models import AssignmentStatus, PlanningChecklistItem, SlotChecklistTick
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._planning import assign, headers_for, send
from tests._users import make_user

URL = "/api/community/planning/checklist/"


@pytest.fixture
def manager():
    return headers_for(PermissionKey.MANAGE_EVENT_PLANNING)


def _texts(api_client, headers):
    return [i["text"] for i in send(api_client, "get", URL, headers=headers).json()]


@pytest.mark.django_db
class TestChecklistItems:
    def test_planner_reads_seeded_list(self, api_client):
        response = send(
            api_client, "get", URL, headers=headers_for(PermissionKey.VIEW_EVENT_PLANNING)
        )
        assert response.status_code == 200
        assert response.json()[0]["text"] == "secure venue"

    def test_non_planner_blocked(self, api_client):
        assert send(api_client, "get", URL, headers=headers_for()).status_code == 403

    def test_create_appends_trimmed(self, api_client, manager):
        response = send(api_client, "post", URL, {"text": "  book a room ", "detail": ""}, manager)
        assert response.status_code == 201
        assert response.json()["text"] == "book a room"
        assert _texts(api_client, manager)[-1] == "book a room"

    def test_blank_text_rejected(self, api_client, manager):
        assert send(api_client, "post", URL, {"text": "  "}, manager).status_code == 422

    def test_update_and_delete(self, api_client, manager):
        item = PlanningChecklistItem.objects.first()
        url = f"{URL}{item.id}/"
        response = send(api_client, "patch", url, {"detail": "call ahead"}, manager)
        assert response.json() == {"id": str(item.id), "text": item.text, "detail": "call ahead"}
        assert send(api_client, "delete", url, headers=manager).status_code == 204
        assert send(api_client, "delete", url, headers=manager).status_code == 404

    @pytest.mark.parametrize(
        ("method", "suffix", "body"),
        [("post", "", {"text": "x"}), ("patch", "{id}/", {"text": "x"}), ("delete", "{id}/", None)],
    )
    def test_planners_cannot_edit(self, api_client, method, suffix, body):
        url = URL + suffix.format(id=PlanningChecklistItem.objects.first().id)
        headers = headers_for(PermissionKey.VIEW_EVENT_PLANNING)
        assert send(api_client, method, url, body, headers).status_code == 403

    def test_move_swaps_neighbours_and_stops_at_ends(self, api_client, manager):
        first, second = PlanningChecklistItem.objects.all()[:2]
        response = send(api_client, "post", f"{URL}{second.id}/move/", {"direction": "up"}, manager)
        assert [i["text"] for i in response.json()[:2]] == [second.text, first.text]
        response = send(api_client, "post", f"{URL}{second.id}/move/", {"direction": "up"}, manager)
        assert response.json()[0]["text"] == second.text


@pytest.mark.django_db
class TestChecklistTicks:
    def _url(self, slot, item):
        return f"/api/community/planning/slots/{slot.id}/checklist/{item.id}/"

    def test_committed_planner_ticks_and_unticks(self, api_client, year):
        me = make_user(PermissionKey.VIEW_EVENT_PLANNING)
        slot = year.slots.first()
        assign(slot, me, AssignmentStatus.COMMITTED)
        item = PlanningChecklistItem.objects.first()
        headers = auth_headers_for(me)
        response = send(api_client, "put", self._url(slot, item), {"done": True}, headers)
        assert response.json() == {"done_ids": [str(item.id)]}
        assert SlotChecklistTick.objects.get().done_by == me
        mine = send(api_client, "get", "/api/community/planning/me/", headers=headers).json()
        assert mine[0]["checklist_done_ids"] == [str(item.id)]
        response = send(api_client, "put", self._url(slot, item), {"done": False}, headers)
        assert response.json() == {"done_ids": []}

    def test_ticking_twice_keeps_first_ticker(self, api_client, year, manager):
        slot, item = year.slots.first(), PlanningChecklistItem.objects.first()
        first = make_user(PermissionKey.MANAGE_EVENT_PLANNING)
        send(api_client, "put", self._url(slot, item), {"done": True}, auth_headers_for(first))
        send(api_client, "put", self._url(slot, item), {"done": True}, manager)
        assert SlotChecklistTick.objects.get().done_by == first

    @pytest.mark.parametrize("status", [AssignmentStatus.PROPOSED, AssignmentStatus.DECLINED, None])
    def test_only_committed_planners_tick(self, api_client, year, status):
        me = make_user(PermissionKey.VIEW_EVENT_PLANNING)
        slot = year.slots.first()
        if status:
            assign(slot, me, status)
        url = self._url(slot, PlanningChecklistItem.objects.first())
        response = send(api_client, "put", url, {"done": True}, auth_headers_for(me))
        assert response.status_code == 403
