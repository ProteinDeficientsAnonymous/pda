import pytest
from community.planning._access import can_manage_planning, can_view_planning
from users.permissions import PermissionKey

from tests._users import make_user


@pytest.mark.django_db
class TestPlanningAccess:
    def test_view_holder_can_view(self):
        user = make_user(PermissionKey.VIEW_EVENT_PLANNING)
        assert can_view_planning(user)

    def test_manage_holder_can_view_and_manage(self):
        user = make_user(PermissionKey.MANAGE_EVENT_PLANNING)
        assert can_view_planning(user)
        assert can_manage_planning(user)

    def test_member_cannot_view(self):
        assert not can_view_planning(make_user())

    def test_view_holder_cannot_manage(self):
        assert not can_manage_planning(make_user(PermissionKey.VIEW_EVENT_PLANNING))
