import uuid

import pytest
from users.models import MembershipStatus
from users.roles import Role

from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_attendance_paused, make_user

TOOL = "set_member_roles"


@pytest.fixture
def member(db):
    user = make_user(first_name="Sam")
    user.roles.add(Role.objects.get(name="member", is_default=True))
    return user


@pytest.fixture
def club_rep(db):
    return Role.objects.create(name="club rep", permissions=[])


@pytest.fixture
def greeter(db):
    return Role.objects.create(name="greeter", permissions=[])


def _call(user, member, add=(), remove=(), **extra) -> dict:
    return run_tool(
        user,
        TOOL,
        member_id=str(member.pk),
        add_role_ids=[str(r.pk) for r in add],
        remove_role_ids=[str(r.pk) for r in remove],
        **extra,
    )


def _role_names(member) -> set[str]:
    return set(member.roles.values_list("name", flat=True))


@pytest.mark.django_db
class TestListRoles:
    def test_lists_ids_and_names(self, manage_users_user, club_rep):
        roles = run_tool(manage_users_user, "list_roles")["roles"]
        assert {"id": str(club_rep.pk), "name": "club rep", "is_default": False} in roles

    def test_hidden_without_a_role_permission(self):
        assert "list_roles" not in tool_names(make_user())


@pytest.mark.django_db
class TestSetMemberRoles:
    def test_needs_manage_users(self):
        assert TOOL not in tool_names(make_user())

    def test_preview_shows_current_and_resulting_roles_and_changes_nothing(
        self, manage_users_user, member, club_rep, greeter
    ):
        member.roles.add(greeter)

        preview = _call(manage_users_user, member, add=[club_rep])

        assert preview["confirm_token"]
        assert {r["name"] for r in preview["current_roles"]} == {"member", "greeter"}
        assert {r["name"] for r in preview["resulting_roles"]} == {"member", "greeter", "club rep"}
        assert _role_names(member) == {"member", "greeter"}

    def test_confirm_adds_without_dropping_other_roles(
        self, manage_users_user, member, club_rep, greeter
    ):
        member.roles.add(greeter)
        token = _call(manage_users_user, member, add=[club_rep])["confirm_token"]

        result = _call(manage_users_user, member, add=[club_rep], confirm_token=token)

        assert {r["name"] for r in result["roles"]} == {"member", "greeter", "club rep"}
        assert _role_names(member) == {"member", "greeter", "club rep"}

    def test_confirm_removes_one_role(self, manage_users_user, member, club_rep, greeter):
        member.roles.add(club_rep, greeter)
        token = _call(manage_users_user, member, remove=[club_rep])["confirm_token"]

        _call(manage_users_user, member, remove=[club_rep], confirm_token=token)

        assert _role_names(member) == {"member", "greeter"}

    def test_token_is_bound_to_the_current_roles(
        self, manage_users_user, member, club_rep, greeter
    ):
        token = _call(manage_users_user, member, add=[club_rep])["confirm_token"]
        member.roles.add(greeter)

        assert "fresh preview" in tool_error(
            manage_users_user,
            TOOL,
            member_id=str(member.pk),
            add_role_ids=[str(club_rep.pk)],
            confirm_token=token,
        )

    @pytest.mark.parametrize(
        "status", [MembershipStatus.GUIDELINES_PAUSED, MembershipStatus.ARCHIVED]
    )
    def test_refuses_paused_and_archived_members(self, manage_users_user, club_rep, status):
        target = make_user(membership_status=status)
        assert "roles can only be changed for active members" in tool_error(
            manage_users_user,
            TOOL,
            member_id=str(target.pk),
            add_role_ids=[str(club_rep.pk)],
        )

    def test_refuses_attendance_paused_members(self, manage_users_user, club_rep):
        target = make_attendance_paused()
        assert "attendance paused" in tool_error(
            manage_users_user, TOOL, member_id=str(target.pk), add_role_ids=[str(club_rep.pk)]
        )

    def test_rejects_an_unknown_member(self, manage_users_user, club_rep):
        missing = str(uuid.uuid4())
        assert f"no member with id {missing}" in tool_error(
            manage_users_user, TOOL, member_id=missing, add_role_ids=[str(club_rep.pk)]
        )

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            ({}, "give add_role_ids"),
            ({"add_role_ids": ["nope"]}, "unknown role ids: nope"),
        ],
    )
    def test_rejects_bad_arguments(self, manage_users_user, member, args, message):
        assert message in tool_error(manage_users_user, TOOL, member_id=str(member.pk), **args)

    def test_rejects_a_role_both_added_and_removed(self, manage_users_user, member, club_rep):
        assert "both added and removed" in tool_error(
            manage_users_user,
            TOOL,
            member_id=str(member.pk),
            add_role_ids=[str(club_rep.pk)],
            remove_role_ids=[str(club_rep.pk)],
        )

    def test_rejects_a_no_op(self, manage_users_user, member, club_rep):
        member.roles.add(club_rep)
        assert "nothing to do" in tool_error(
            manage_users_user,
            TOOL,
            member_id=str(member.pk),
            add_role_ids=[str(club_rep.pk)],
        )

    def test_only_an_admin_can_grant_admin(self, manage_users_user, member):
        admin = Role.objects.get(name="admin", is_default=True)
        assert "cannot_grant_admin" in tool_error(
            manage_users_user, TOOL, member_id=str(member.pk), add_role_ids=[str(admin.pk)]
        )

    def test_member_role_cannot_be_removed(self, manage_users_user, member):
        member_role = Role.objects.get(name="member", is_default=True)
        assert "member_role_required" in tool_error(
            manage_users_user, TOOL, member_id=str(member.pk), remove_role_ids=[str(member_role.pk)]
        )
