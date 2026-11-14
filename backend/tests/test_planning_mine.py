import pytest
from community.models import AssignmentStatus, PlanningYear, SlotAssignment
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._planning import headers_for, send
from tests._users import make_user

VIEW = PermissionKey.VIEW_EVENT_PLANNING
URL = "/api/community/planning/me/"
S = AssignmentStatus


def get_mine(api_client, headers):
    return send(api_client, "get", URL, headers=headers)


def assign(slot, user, status=S.PROPOSED):
    return SlotAssignment.objects.create(slot=slot, user=user, status=status)


@pytest.mark.django_db
class TestMySlots:
    def test_requires_view(self, api_client, year):
        assert get_mine(api_client, headers_for()).status_code == 403

    def test_lists_only_own_proposed_and_committed(self, api_client, year):
        me = make_user(VIEW)
        s = list(year.slots.all()[:5])
        proposed = assign(s[0], me)
        committed = assign(s[1], me, S.COMMITTED)
        assign(s[2], me, S.DECLINED)
        assign(s[3], me, S.WITHDRAWN)
        assign(s[4], make_user(VIEW))
        data = get_mine(api_client, auth_headers_for(me)).json()
        assert [(r["assignment_id"], r["status"]) for r in data] == [
            (str(proposed.id), S.PROPOSED),
            (str(committed.id), S.COMMITTED),
        ]
        assert data[0]["year"] == 2027
        assert data[0]["slot"]["id"] == str(s[0].id)

    def test_ordered_by_year_then_slot_order(self, api_client, year):
        me = make_user(VIEW)
        earlier = PlanningYear.create_with_default_slots(2026)
        late, early = list(year.slots.all()[:2])[::-1]
        assign(late, me)
        assign(early, me)
        earlier_slot = earlier.slots.get(order=1)
        assign(earlier_slot, me)
        data = get_mine(api_client, auth_headers_for(me)).json()
        assert [(r["year"], r["slot"]["order"]) for r in data] == [
            (2026, earlier_slot.order),
            (2027, early.order),
            (2027, late.order),
        ]

    def test_teammates_are_other_active_rows_on_the_slot(self, api_client, year):
        me = make_user(VIEW, first_name="me")
        slot = year.slots.first()
        assign(slot, me)
        assign(slot, make_user(VIEW, first_name="bea"), S.COMMITTED)
        assign(slot, make_user(VIEW, first_name="cy"))
        assign(slot, make_user(VIEW, first_name="dropped"), S.DECLINED)
        assign(slot, make_user(VIEW, first_name="gone"), S.WITHDRAWN)
        (row,) = get_mine(api_client, auth_headers_for(me)).json()
        assert sorted((t["name"], t["status"]) for t in row["teammates"]) == [
            ("bea", S.COMMITTED),
            ("cy", S.PROPOSED),
        ]

    def test_teammate_name_respects_hide_last_name(self, api_client, year):
        me = make_user(VIEW)
        slot = year.slots.first()
        assign(slot, me)
        assign(slot, make_user(VIEW, first_name="bea", last_name="smith", hide_last_name=True))
        (row,) = get_mine(api_client, auth_headers_for(me)).json()
        assert row["teammates"][0]["name"] == "bea"

    def test_query_count_does_not_grow_with_teammates(
        self, api_client, year, django_assert_max_num_queries
    ):
        me = make_user(VIEW)
        slots = list(year.slots.all()[:3])
        for slot in slots:
            assign(slot, me)
        assign(slots[0], make_user(VIEW))
        headers = auth_headers_for(me)
        with django_assert_max_num_queries(12) as small:
            get_mine(api_client, headers)
        for slot in slots:
            for _ in range(3):
                assign(slot, make_user(VIEW))
        with django_assert_max_num_queries(len(small.captured_queries)):
            get_mine(api_client, headers)
