import pytest
from users.permissions import PermissionKey
from users.roles import Role

_JSON = "application/json"


def _event(event_type: str) -> dict:
    return {
        "title": "Matrix",
        "datetime_tbd": True,
        "event_type": event_type,
        "visibility": "public",
    }


# method, path, JSON body (None for GET), status after the key is granted.
_ROUTES: dict[PermissionKey, tuple[str, str, dict | None, int]] = {
    PermissionKey.CREATE_USER: (
        "post",
        "/api/auth/create-user/",
        {"phone_number": "+12025550991", "first_name": "Matrix", "email": "matrix@e.com"},
        201,
    ),
    PermissionKey.MANAGE_USERS: ("get", "/api/auth/users/", None, 200),
    PermissionKey.MANAGE_ROLES: ("get", "/api/auth/roles/", None, 200),
    PermissionKey.APPROVE_JOIN_REQUESTS: ("get", "/api/community/join-requests/", None, 200),
    PermissionKey.MANAGE_EVENTS: ("get", "/api/community/event-flags/", None, 200),
    PermissionKey.EDIT_GUIDELINES: ("patch", "/api/community/guidelines/", {}, 200),
    PermissionKey.EDIT_FAQ: ("patch", "/api/community/faq/", {}, 200),
    PermissionKey.EDIT_HOMEPAGE: ("patch", "/api/community/home/", {}, 200),
    PermissionKey.EDIT_JOIN_QUESTIONS: (
        "post",
        "/api/community/join-form/questions/",
        {"label": "Matrix"},
        201,
    ),
    PermissionKey.MANAGE_SURVEYS: ("get", "/api/community/surveys/admin/", None, 200),
    PermissionKey.TAG_OFFICIAL_EVENT: ("post", "/api/community/events/", _event("official"), 201),
    PermissionKey.TAG_CLUB_EVENT: ("post", "/api/community/events/", _event("club"), 201),
    PermissionKey.MANAGE_DOCUMENTS: ("get", "/api/community/docs/folders/", None, 200),
}


def _call(client, key: PermissionKey, headers: dict):
    method, path, body, _ok = _ROUTES[key]
    if body is None:
        return getattr(client, method)(path, **headers)
    return getattr(client, method)(path, body, content_type=_JSON, **headers)


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.parametrize("key", list(PermissionKey), ids=lambda key: key.value)
def test_permission_key_absent_rejected_then_granted_allowed(
    api_client, auth_headers, test_user, key
):
    denied = _call(api_client, key, auth_headers)
    assert denied.status_code == 403

    role = Role.objects.create(name=f"matrix-{key.value}", permissions=[key])
    test_user.roles.add(role)
    allowed = _call(api_client, key, auth_headers)
    assert allowed.status_code == _ROUTES[key][3]
