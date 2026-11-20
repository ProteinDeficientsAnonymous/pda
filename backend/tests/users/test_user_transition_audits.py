import pytest
from audit.models import AuditLogEntry, AuditTargetType
from django.test import TestCase
from tests._auth import auth_headers_for
from users.models import User

pytestmark = pytest.mark.django_db


def _send(method, *args, **kwargs):
    with TestCase.captureOnCommitCallbacks(execute=True):
        response = method(*args, content_type="application/json", **kwargs)
    assert response.status_code in (200, 201, 204), response.content
    return response


def _assert_entry(action: str, actor: User, target: User) -> AuditLogEntry:
    entry = AuditLogEntry.objects.get(action=action)
    assert entry.actor == actor
    assert (entry.target_type, entry.target_id) == (AuditTargetType.USER, str(target.pk))
    return entry


def test_guidelines_pause_and_unpause(api_client, manage_users_user, manage_users_headers, member):
    url = f"/api/auth/users/{member.pk}/"
    _send(api_client.patch, url, {"guidelines_paused": True}, **manage_users_headers)
    _send(api_client.patch, url, {"guidelines_paused": False}, **manage_users_headers)

    for action in ("user_paused", "user_unpaused"):
        entry = _assert_entry(action, manage_users_user, member)
        assert entry.details["full_name"] == member.full_name
    assert "removed_role_ids" in AuditLogEntry.objects.get(action="user_paused").details


def test_attendance_pause(api_client, manage_users_user, manage_users_headers, member):
    url = f"/api/auth/users/{member.pk}/"
    _send(api_client.patch, url, {"attendance_paused": True}, **manage_users_headers)

    entry = _assert_entry("user_attendance_paused", manage_users_user, member)
    assert entry.details["full_name"] == member.full_name
    assert "removed_role_ids" in entry.details


def test_archived(api_client, manage_users_user, manage_users_headers, member):
    _send(api_client.delete, f"/api/auth/users/{member.pk}/", **manage_users_headers)

    entry = _assert_entry("user_archived", manage_users_user, member)
    assert entry.details["full_name"] == member.full_name


def test_self_deleted(api_client, member):
    body = {"password": "memberpass123"}
    _send(api_client.post, "/api/auth/me/delete/", body, **auth_headers_for(member))

    entry = _assert_entry("user_self_deleted", member, member)
    assert entry.details["full_name"] == member.full_name


def test_pause_with_rename_logs_both(api_client, manage_users_user, manage_users_headers, member):
    body = {"guidelines_paused": True, "first_name": "Renamed"}
    _send(api_client.patch, f"/api/auth/users/{member.pk}/", body, **manage_users_headers)

    _assert_entry("user_paused", manage_users_user, member)
    entry = _assert_entry("user_updated", manage_users_user, member)
    assert entry.details["fields_changed"] == ["first_name"]
