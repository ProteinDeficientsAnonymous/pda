import pytest
from audit.models import AuditLogEntry, AuditTargetType
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._mcp_tool_helpers import run_tool, tool_error, tool_names

pytestmark = pytest.mark.django_db


@pytest.fixture
def auditor(db):
    user = User.objects.create_user(phone_number="+12025550777", first_name="Audra")
    user.roles.add(Role.objects.create(name="auditor", permissions=[PermissionKey.VIEW_AUDIT_LOG]))
    return user


def _entry(action, actor, target, details=None):
    return AuditLogEntry.objects.create(
        action=action,
        actor=actor,
        actor_label=actor.full_name,
        target_type=target[0],
        target_id=target[1],
        details=details or {},
        level=20,
    )


def test_hidden_and_forbidden_without_permission(test_user):
    assert "audit_history" not in tool_names(test_user)
    assert "permission" in tool_error(test_user, "audit_history")


def test_what_happened_to_a_member(auditor, test_user):
    member = str(test_user.pk)
    _entry(
        "join_request_approved", auditor, (AuditTargetType.JOIN_REQUEST, "jr"), {"user_id": member}
    )
    _entry("user_paused", auditor, (AuditTargetType.USER, member))
    _entry("user_paused", auditor, (AuditTargetType.USER, str(auditor.pk)))

    body = run_tool(auditor, "audit_history", filters={"member_id": member})

    assert body["total"] == 2
    assert {(e["action"], e["actor_label"]) for e in body["entries"]} == {
        ("join_request_approved", "Audra"),
        ("user_paused", "Audra"),
    }


def test_recent_actions_by_an_admin(auditor, test_user):
    _entry("user_archived", auditor, (AuditTargetType.USER, str(test_user.pk)))
    _entry("role_created", test_user, (AuditTargetType.ROLE, "r1"))

    body = run_tool(auditor, "audit_history", filters={"actor_id": str(auditor.pk)}, limit=1)

    assert [e["action"] for e in body["entries"]] == ["user_archived"]
    assert (body["total"], body["next_offset"]) == (1, None)
