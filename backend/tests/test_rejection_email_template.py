import pytest
from community._validation import Code
from community.models import RejectionEmailTemplate, RejectionReason

from tests._asserts import assert_error_code


@pytest.mark.django_db
class TestRejectionEmailTemplate:
    def test_get_returns_defaults(self, api_client, auth_headers):
        response = api_client.get("/api/community/rejection-email/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "${REASON}" in data["body"]
        assert set(data["reasons"]) == {
            RejectionReason.VEGETARIAN,
            RejectionReason.NOT_VEGAN,
            RejectionReason.QUESTIONS_NOT_ANSWERED,
        }

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.get("/api/community/rejection-email/").status_code == 401

    def test_patch_updates_body_and_reasons(self, api_client, vettor_headers):
        response = api_client.patch(
            "/api/community/rejection-email/",
            data={"body": "sorry ${REASON}", "reasons": {"vegetarian": "go vegan"}},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        template = RejectionEmailTemplate.get()
        assert template.body == "sorry ${REASON}"
        assert template.vegetarian_text == "go vegan"
        assert response.json()["reasons"]["vegetarian"] == "go vegan"

    def test_patch_without_permission_returns_403(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/community/rejection-email/",
            data={"body": "x"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_blank_body_is_rejected(self, api_client, vettor_headers):
        response = api_client.patch(
            "/api/community/rejection-email/",
            data={"body": "   "},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.RejectionEmail.BODY_REQUIRED, "body")

    def test_blank_reason_text_is_rejected(self, api_client, vettor_headers):
        response = api_client.patch(
            "/api/community/rejection-email/",
            data={"reasons": {"not_vegan": ""}},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.RejectionEmail.REASON_TEXT_REQUIRED)

    def test_other_is_not_an_editable_reason(self, api_client, vettor_headers):
        response = api_client.patch(
            "/api/community/rejection-email/",
            data={"reasons": {"other": "nope"}},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.JoinRequest.INVALID_REJECTION_REASON, "reasons")
