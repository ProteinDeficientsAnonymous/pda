import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.models import MemberRestoredEmailTemplate
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._users import make_user

URL = "/api/community/member-restored-email/"


@pytest.fixture
def approver_headers(db):
    return auth_headers_for(make_user(PermissionKey.APPROVE_JOIN_REQUESTS))


def _patch(api_client, body, headers):
    return api_client.patch(URL, data={"body": body}, content_type="application/json", **headers)


@pytest.mark.django_db
class TestMemberRestoredEmailEndpoints:
    def test_get_returns_default_body_with_whatsapp_link(self, api_client, auth_headers):
        response = api_client.get(URL, **auth_headers)
        assert response.status_code == 200
        assert "${WHATSAPP_LINK}" in response.json()["body"]

    def test_get_returns_the_stored_body(self, api_client, auth_headers):
        MemberRestoredEmailTemplate.objects.update_or_create(pk=1, defaults={"body": "edited"})
        assert api_client.get(URL, **auth_headers).json()["body"] == "edited"

    def test_get_unauthenticated_returns_401(self, api_client):
        assert api_client.get(URL).status_code == 401

    def test_approver_updates_body(
        self, api_client, approver_headers, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            response = _patch(api_client, "hi ${FIRST_NAME} ${WHATSAPP_LINK}", approver_headers)
        assert response.status_code == 200
        assert MemberRestoredEmailTemplate.get().body == "hi ${FIRST_NAME} ${WHATSAPP_LINK}"
        assert AuditLogEntry.objects.filter(
            action="member_restored_email_updated",
            target_type=AuditTargetType.MEMBER_RESTORED_EMAIL,
        ).exists()

    def test_patch_unauthenticated_returns_401(self, api_client):
        assert _patch(api_client, "x", {}).status_code == 401

    def test_without_permission_returns_403(self, api_client, auth_headers):
        response = _patch(api_client, "sneaky edit", auth_headers)
        assert response.status_code == 403
        assert_error_code(response, "perm.denied")

    def test_empty_body_rejected(self, api_client, approver_headers):
        response = _patch(api_client, "   ", approver_headers)
        assert response.status_code == 422
        assert_error_code(response, "member_restored_email.body_required", expected_field="body")

    def test_too_long_body_rejected(self, api_client, approver_headers):
        response = _patch(api_client, "x" * 5000, approver_headers)
        assert response.status_code == 422
        entry = assert_error_code(
            response, "member_restored_email.body_too_long", expected_field="body"
        )
        assert entry["params"]["max_length"] == 4000
