import pytest
from users.roles import Role

from tests._mcp_tool_helpers import run_tool, tool_names
from tests._users import make_user


@pytest.fixture
def club_rep(db):
    return Role.objects.create(name="club rep", permissions=[])


@pytest.mark.django_db
class TestListRoles:
    def test_lists_ids_and_names(self, manage_users_user, club_rep):
        roles = run_tool(manage_users_user, "list_roles")["roles"]
        assert {"id": str(club_rep.pk), "name": "club rep", "is_default": False} in roles

    def test_hidden_without_a_role_permission(self):
        assert "list_roles" not in tool_names(make_user())
