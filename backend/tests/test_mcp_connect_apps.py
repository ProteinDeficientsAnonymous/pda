import pytest
from django.utils import timezone
from mcp_gateway.models import OAuthGrant

from tests._mcp_helpers import make_client, make_grant

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
