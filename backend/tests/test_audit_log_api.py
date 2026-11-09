from datetime import timedelta

import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.validation import Code
from django.utils import timezone
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for

pytestmark = pytest.mark.django_db
URL = "/api/audit/"


@pytest.fixture
def auditor(db):
    user = User.objects.create_user(phone_number="+12025550777", first_name="Audra")
    user.roles.add(Role.objects.create(name="auditor", permissions=[PermissionKey.VIEW_AUDIT_LOG]))
    return user


@pytest.fixture
def member(db):
    return User.objects.create_user(phone_number="+12025550778", first_name="Mem")


def _entry(action, actor=None, target=("", ""), details=None, days_ago=0):
    target_type, target_id = target
    entry = AuditLogEntry.objects.create(
        action=action,
        actor=actor,
        actor_label=actor.full_name if actor else "anonymous",
        target_type=target_type,
        target_id=target_id,
        details=details or {},
        level=20,
    )
    if days_ago:
        entry.created_at = timezone.now() - timedelta(days=days_ago)
        entry.save(update_fields=["created_at"])
    return entry


def _get(api_client, user, **params):
    response = api_client.get(URL, params, **auth_headers_for(user))
    assert response.status_code == 200, response.content
    return response.json()


def _actions(body) -> list[str]:
    return [e["action"] for e in body["entries"]]


def test_requires_permission(api_client, member):
    response = api_client.get(URL, **auth_headers_for(member))

    assert response.status_code == 403
    assert_error_code(response, Code.Perm.DENIED)


def test_member_history_includes_linked_join_requests(api_client, auditor, member):
    _entry("user_paused", auditor, (AuditTargetType.USER, str(member.pk)))
    _entry(
        "join_request_approved",
        auditor,
        (AuditTargetType.JOIN_REQUEST, "jr"),
        {"user_id": str(member.pk)},
    )
    _entry("user_paused", auditor, (AuditTargetType.USER, str(auditor.pk)))

    body = _get(api_client, auditor, member_id=str(member.pk))

    assert sorted(_actions(body)) == ["join_request_approved", "user_paused"]
    assert body["entries"][0]["actor_label"] == "Audra"


def test_filters_by_actor_action_target_and_dates(api_client, auditor, member):
    _entry("user_archived", auditor, (AuditTargetType.USER, str(member.pk)), days_ago=10)
    _entry("user_archived", member, (AuditTargetType.USER, str(auditor.pk)), days_ago=2)
    _entry("role_created", auditor, (AuditTargetType.ROLE, "r1"), days_ago=2)
    since = (timezone.now() - timedelta(days=5)).isoformat()

    assert _get(api_client, auditor, actor_id=str(auditor.pk), since=since)["total"] == 1
    assert _get(api_client, auditor, action="user_archived")["total"] == 2
    assert _get(api_client, auditor, target_type=AuditTargetType.ROLE, target_id="r1")["total"] == 1
    until = (timezone.now() - timedelta(days=5)).isoformat()
    assert _actions(_get(api_client, auditor, until=until)) == ["user_archived"]


def test_paginates_newest_first(api_client, auditor):
    for days_ago in (3, 2, 1):
        _entry(f"action_{days_ago}", days_ago=days_ago)

    first = _get(api_client, auditor, limit=2)
    second = _get(api_client, auditor, limit=2, offset=first["next_offset"])

    assert (_actions(first), first["total"], first["next_offset"]) == (
        ["action_1", "action_2"],
        3,
        2,
    )
    assert (_actions(second), second["next_offset"]) == (["action_3"], None)
