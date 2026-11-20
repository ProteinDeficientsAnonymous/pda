import json

import pytest
from community.models import EditablePage
from users.permissions import PermissionKey

from tests._planning import headers_for, send

URL = "/api/community/pages/planning-guidelines/"


def _doc(text):
    return json.dumps(
        {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
        }
    )


@pytest.mark.django_db
class TestPlanningGuidelines:
    def test_seeded_on_first_read(self, api_client):
        response = send(
            api_client, "get", URL, headers=headers_for(PermissionKey.VIEW_EVENT_PLANNING)
        )
        assert response.status_code == 200
        html = response.json()["content_html"]
        assert "<h2>restaurant meetups</h2>" in html
        assert "<li>principles gi</li>" in html
        assert EditablePage.objects.filter(slug="planning-guidelines").count() == 1

    def test_manager_can_read(self, api_client):
        headers = headers_for(PermissionKey.MANAGE_EVENT_PLANNING)
        assert send(api_client, "get", URL, headers=headers).status_code == 200

    def test_anon_and_non_planner_blocked(self, api_client):
        assert send(api_client, "get", URL).status_code == 403
        headers = headers_for(PermissionKey.EDIT_GUIDELINES)
        assert send(api_client, "get", URL, headers=headers).status_code == 403

    def test_manager_edits_keep_over_seed(self, api_client):
        headers = headers_for(PermissionKey.MANAGE_EVENT_PLANNING)
        response = send(api_client, "patch", URL, {"content_pm": _doc("new rules")}, headers)
        assert response.status_code == 200
        assert send(api_client, "get", URL, headers=headers).json()["content_html"] == (
            "<p>new rules</p>"
        )

    @pytest.mark.parametrize(
        "permission", [PermissionKey.VIEW_EVENT_PLANNING, PermissionKey.EDIT_GUIDELINES]
    )
    def test_only_managers_edit(self, api_client, permission):
        response = send(
            api_client, "patch", URL, {"content_pm": _doc("x")}, headers_for(permission)
        )
        assert response.status_code == 403


PROTOCOL_URL = "/api/community/pages/event-protocol/"


@pytest.mark.django_db
class TestEventProtocolPage:
    def test_planning_manager_edits(self, api_client):
        headers = headers_for(PermissionKey.MANAGE_EVENT_PLANNING)
        response = send(
            api_client, "patch", PROTOCOL_URL, {"content_pm": _doc("be early")}, headers
        )
        assert response.status_code == 200
        assert response.json()["content_html"] == "<p>be early</p>"

    @pytest.mark.parametrize(
        "permission", [PermissionKey.VIEW_EVENT_PLANNING, PermissionKey.EDIT_GUIDELINES]
    )
    def test_others_cannot_edit(self, api_client, permission):
        response = send(
            api_client, "patch", PROTOCOL_URL, {"content_pm": _doc("x")}, headers_for(permission)
        )
        assert response.status_code == 403

    def test_any_member_can_read(self, api_client):
        assert send(api_client, "get", PROTOCOL_URL, headers=headers_for()).status_code == 200
