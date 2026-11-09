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


def test_admin_created(api_client, manage_users_user, manage_users_headers):
    body = {"phone_number": "+12025551234", "first_name": "New", "email": "new@example.com"}
    _send(api_client.post, "/api/auth/create-user/", body, **manage_users_headers)

    created = User.objects.get(phone_number="+12025551234")
    entry = _assert_entry("user_created", manage_users_user, created)
    assert entry.details["full_name"] == created.full_name


def test_bulk_created_audits_each_user(api_client, manage_users_user, manage_users_headers):
    phones = ["+12025551301", "+12025551302"]
    body = {"phone_numbers": phones}
    _send(api_client.post, "/api/auth/bulk-create-users/", body, **manage_users_headers)

    entries = AuditLogEntry.objects.filter(action="user_created")
    created_ids = {str(u.pk) for u in User.objects.filter(phone_number__in=phones)}
    assert {e.target_id for e in entries} == created_ids
    assert all(e.actor == manage_users_user and e.details == {"bulk": True} for e in entries)


@pytest.mark.parametrize(
    ("field", "paused_action", "unpaused_action"),
    [
        ("is_paused", "user_paused", "user_unpaused"),
        ("attendance_paused", "user_attendance_paused", "user_attendance_unpaused"),
    ],
)
def test_pause_and_unpause(  # noqa: PLR0913
    api_client,
    manage_users_user,
    manage_users_headers,
    member,
    field,
    paused_action,
    unpaused_action,
):
    url = f"/api/auth/users/{member.pk}/"
    _send(api_client.patch, url, {field: True}, **manage_users_headers)
    _send(api_client.patch, url, {field: False}, **manage_users_headers)

    for action in (paused_action, unpaused_action):
        entry = _assert_entry(action, manage_users_user, member)
        assert entry.details["full_name"] == member.full_name


def test_archived(api_client, manage_users_user, manage_users_headers, member):
    _send(api_client.delete, f"/api/auth/users/{member.pk}/", **manage_users_headers)

    entry = _assert_entry("user_archived", manage_users_user, member)
    assert entry.details["full_name"] == member.full_name


def test_self_deleted(api_client, member):
    body = {"password": "memberpass123"}
    _send(api_client.post, "/api/auth/me/delete/", body, **auth_headers_for(member))

    _assert_entry("user_self_deleted", member, member)
