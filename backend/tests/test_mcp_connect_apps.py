import asyncio

import pytest
from audit.models import AuditLogEntry
from django.utils import timezone
from mcp_gateway.models import OAuthGrant, OAuthToken
from mcp_gateway.provider import PdaOAuthProvider

from tests._asserts import assert_error_code
from tests._mcp_helpers import make_client, make_grant, make_tokens

pytestmark = pytest.mark.django_db


def test_list_my_apps_excludes_revoked(api_client, auth_headers, test_user):
    live = make_grant(test_user, make_client(name="claude"))
    dead = make_grant(test_user, make_client(name="old"))
    OAuthGrant.objects.filter(pk=dead.pk).update(revoked_at=timezone.now())
    resp = api_client.get("/api/connect/apps/", **auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert [a["id"] for a in body] == [str(live.id)]
    assert body[0]["client_name"] == "claude"
    assert body[0]["last_used_at"] is None


def test_list_my_apps_excludes_other_users(api_client, auth_headers, manage_users_user):
    make_grant(manage_users_user)
    assert api_client.get("/api/connect/apps/", **auth_headers).json() == []


def test_list_my_apps_requires_auth(api_client):
    assert api_client.get("/api/connect/apps/").status_code == 401


def _revoke_url(grant) -> str:
    return f"/api/connect/apps/{grant.id}/"


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_revoke_own_app_kills_tokens(api_client, auth_headers, test_user):
    grant = make_grant(test_user)
    access = make_tokens(grant)
    assert asyncio.run(PdaOAuthProvider().load_access_token(access)) is not None
    assert api_client.delete(_revoke_url(grant), **auth_headers).status_code == 204
    assert asyncio.run(PdaOAuthProvider().load_access_token(access)) is None
    grant.refresh_from_db()
    assert grant.revoked_at is not None
    assert not OAuthToken.objects.filter(grant=grant, revoked_at__isnull=True).exists()


def test_revoke_own_app_twice_404(api_client, auth_headers, test_user):
    grant = make_grant(test_user)
    api_client.delete(_revoke_url(grant), **auth_headers)
    resp = api_client.delete(_revoke_url(grant), **auth_headers)
    assert resp.status_code == 404
    assert_error_code(resp, "connect.app_not_found")


def test_cannot_revoke_someone_elses_app_404(api_client, auth_headers, manage_users_user):
    grant = make_grant(manage_users_user)
    make_tokens(grant)
    resp = api_client.delete(_revoke_url(grant), **auth_headers)
    assert resp.status_code == 404
    assert_error_code(resp, "connect.app_not_found")
    grant.refresh_from_db()
    assert grant.revoked_at is None
    assert OAuthToken.objects.filter(grant=grant, revoked_at__isnull=True).count() == 2


def test_revoke_requires_auth(api_client, test_user):
    assert api_client.delete(_revoke_url(make_grant(test_user))).status_code == 401


def test_revoke_is_audited(api_client, auth_headers, test_user, django_capture_on_commit_callbacks):
    grant = make_grant(test_user)
    with django_capture_on_commit_callbacks(execute=True):
        api_client.delete(_revoke_url(grant), **auth_headers)
    entry = AuditLogEntry.objects.get(action="mcp_connection_revoked")
    assert entry.target_id == str(grant.id)
    assert entry.details == {"user_id": str(test_user.pk), "by_admin": False}


def _admin_url(user, grant=None) -> str:
    base = f"/api/connect/users/{user.pk}/apps/"
    return base + (f"{grant.id}/" if grant else "")


def test_admin_lists_member_apps(api_client, manage_users_headers, test_user):
    grant = make_grant(test_user, make_client(name="claude"))
    resp = api_client.get(_admin_url(test_user), **manage_users_headers)
    assert resp.status_code == 200
    assert [a["id"] for a in resp.json()] == [str(grant.id)]


def test_admin_list_unknown_user_404(api_client, manage_users_headers):
    resp = api_client.get(
        "/api/connect/users/00000000-0000-0000-0000-000000000000/apps/", **manage_users_headers
    )
    assert resp.status_code == 404
    assert_error_code(resp, "user.not_found")


def test_non_admin_cannot_list_member_apps_403(api_client, auth_headers, manage_users_user):
    make_grant(manage_users_user)
    resp = api_client.get(_admin_url(manage_users_user), **auth_headers)
    assert resp.status_code == 403
    assert_error_code(resp, "perm.denied")
