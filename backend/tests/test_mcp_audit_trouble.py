from datetime import timedelta

import pytest
from audit.models import AuditLogEntry, AuditTargetType
from audit.trouble import ip_hash
from django.utils import timezone
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._mcp_tool_helpers import run_tool, tool_error, tool_names

pytestmark = pytest.mark.django_db

START = timezone.now() - timedelta(days=1)


@pytest.fixture
def auditor(db):
    user = User.objects.create_user(phone_number="+12025550777", first_name="Audra")
    user.roles.add(Role.objects.create(name="auditor", permissions=[PermissionKey.VIEW_AUDIT_LOG]))
    return user


def _entry(action, minutes, *, ip=None, user_id=None, target=("", "")):
    entry = AuditLogEntry.objects.create(
        action=action,
        actor_label="anonymous",
        target_type=target[0],
        target_id=target[1],
        details={"user_id": user_id} if user_id else {},
        ip_address=ip,
        level=30,
    )
    AuditLogEntry.objects.filter(pk=entry.pk).update(created_at=START + timedelta(minutes=minutes))


def _report(user, **kwargs):
    return run_tool(user, "trouble_report", since=START.isoformat(), **kwargs)


def test_hidden_and_forbidden_without_permission(test_user):
    assert "trouble_report" not in tool_names(test_user)
    assert "permission" in tool_error(test_user, "trouble_report", since=START.isoformat())


def test_groups_failures_by_action(auditor):
    _entry("login_failed", 1, ip="203.0.113.5")
    _entry("permission_denied", 2, user_id="m1")
    _entry("permission_denied", 3, target=(AuditTargetType.USER, "m2"))
    _entry("login_success", 4, ip="203.0.113.5")

    body = _report(auditor)

    assert [(a["action"], a["count"], a["members"]) for a in body["actions"]] == [
        ("permission_denied", 2, ["m1", "m2"]),
        ("login_failed", 1, []),
    ]
    sample = body["actions"][1]["samples"][0]
    assert sample["ip"] == ip_hash("203.0.113.5")
    assert "203.0.113.5" not in str(body)
    assert body["truncated"] is False


def test_window_bounds(auditor):
    _entry("login_failed", 0, ip="203.0.113.5")
    _entry("login_failed", 300, ip="203.0.113.5")

    body = _report(auditor, until=(START + timedelta(minutes=200)).isoformat())

    assert body["actions"][0]["count"] == 1


def test_ip_hash_skips_missing_address():
    assert ip_hash(None) is None
    assert len(ip_hash("203.0.113.5") or "") == 10
