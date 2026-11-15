import pytest
from community.models import (
    AssignmentStatus,
    BiannualInterest,
    PlanningAvailability,
    SlotAssignment,
)
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._planning import headers_for, send
from tests._users import make_user

VIEW = PermissionKey.VIEW_EVENT_PLANNING
MANAGE = PermissionKey.MANAGE_EVENT_PLANNING
URL = "/api/community/planning/years/2027/grid/"


def get_grid(api_client, headers):
    return send(api_client, "get", URL, headers=headers)


def availability(year, user, slots=(), interest=BiannualInterest.YES, count=2):
    row = PlanningAvailability.objects.create(
        planning_year=year, user=user, biannual_interest=interest, monthly_count=count
    )
    row.available_slots.set(slots)
    return row


@pytest.mark.django_db
class TestGrid:
    def test_requires_manage(self, api_client, year):
        assert get_grid(api_client, headers_for(VIEW)).status_code == 403
        assert get_grid(api_client, headers_for()).status_code == 403

    def test_unknown_year_404(self, api_client, db):
        assert get_grid(api_client, headers_for(MANAGE)).status_code == 404

    def test_columns_cover_planners_and_submissions(self, api_client, year):
        slot = year.slots.first()
        viewer = make_user(VIEW, first_name="bea", email="")
        availability(year, viewer, [slot], BiannualInterest.MAYBE, 3)
        silent = make_user(VIEW, first_name="al")
        data = get_grid(api_client, headers_for(MANAGE)).json()
        by_id = {c["user_id"]: c for c in data["planners"]}
        assert by_id[str(viewer.id)] == {
            "user_id": str(viewer.id),
            "name": "bea",
            "is_planner": True,
            "has_email": False,
            "submitted": True,
            "biannual_interest": BiannualInterest.MAYBE,
            "monthly_count": 3,
            "available_slot_ids": [str(slot.id)],
        }
        assert by_id[str(silent.id)]["submitted"] is False
        assert by_id[str(silent.id)]["available_slot_ids"] == []
        assert by_id[str(silent.id)]["has_email"] is True
        assert [s["label"] for s in data["slots"]][0] == "january"

    def test_columns_ordered_by_name(self, api_client, year):
        make_user(VIEW, first_name="zed")
        make_user(VIEW, first_name="Amy")
        names = [c["name"] for c in get_grid(api_client, headers_for(MANAGE)).json()["planners"]]
        assert names == sorted(names, key=str.casefold)

    def test_includes_planner_who_lost_the_role(self, api_client, year):
        slot = year.slots.first()
        ex_planner = make_user(first_name="gone")
        availability(year, ex_planner, [slot])
        with_assignment = make_user(first_name="held")
        SlotAssignment.objects.create(slot=slot, user=with_assignment)
        columns = {
            c["user_id"]: c for c in get_grid(api_client, headers_for(MANAGE)).json()["planners"]
        }
        assert columns[str(ex_planner.id)]["is_planner"] is False
        assert columns[str(with_assignment.id)]["is_planner"] is False

    def test_excludes_non_planners_without_activity(self, api_client, year):
        bystander = make_user()
        ids = {c["user_id"] for c in get_grid(api_client, headers_for(MANAGE)).json()["planners"]}
        assert str(bystander.id) not in ids

    def test_assignments_omit_withdrawn(self, api_client, year):
        slot = year.slots.first()
        planner = make_user(VIEW)
        kept = SlotAssignment.objects.create(slot=slot, user=planner)
        other = year.slots.last()
        SlotAssignment.objects.create(slot=other, user=planner, status=AssignmentStatus.WITHDRAWN)
        data = get_grid(api_client, headers_for(MANAGE)).json()
        assert [a["id"] for a in data["assignments"]] == [str(kept.id)]

    def test_query_count_does_not_grow_with_planners(
        self, api_client, year, django_assert_max_num_queries
    ):
        headers = auth_headers_for(make_user(MANAGE))
        slots = list(year.slots.all()[:3])
        for _ in range(2):
            planner = make_user(VIEW)
            availability(year, planner, slots)
            SlotAssignment.objects.create(slot=slots[0], user=planner)
        with django_assert_max_num_queries(12) as small:
            get_grid(api_client, headers)
        for _ in range(5):
            planner = make_user(VIEW)
            availability(year, planner, slots)
            SlotAssignment.objects.create(slot=slots[1], user=planner)
        with django_assert_max_num_queries(len(small.captured_queries)):
            get_grid(api_client, headers)
