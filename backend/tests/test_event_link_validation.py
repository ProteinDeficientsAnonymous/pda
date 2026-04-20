"""Tests for event link URL validation (issue #301).

Validates that:
- Bare domains (no path) are rejected for whatsapp_link, partiful_link, other_link
- Wrong domains are rejected for domain-specific fields
- Valid deep links are accepted
- Empty strings are accepted (links are optional)
"""

import pytest

BASE_EVENT = {
    "title": "Link Test Event",
    "start_datetime": "2026-06-01T18:00:00Z",
}


@pytest.fixture
def manage_events_headers(db):
    from ninja_jwt.tokens import RefreshToken
    from users.models import User
    from users.permissions import PermissionKey
    from users.roles import Role

    user = User.objects.create_user(
        phone_number="+14155559001",
        password="eventmanagerpass123",
        display_name="Link Test Manager",
    )
    role = Role.objects.create(name="link_event_mgr", permissions=[PermissionKey.MANAGE_EVENTS])
    user.roles.add(role)
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestWhatsappLinkValidation:
    def _post(self, api_client, headers, whatsapp_link):
        return api_client.post(
            "/api/community/events/",
            {**BASE_EVENT, "whatsapp_link": whatsapp_link},
            content_type="application/json",
            **headers,
        )

    def test_valid_chat_whatsapp_link(self, api_client, manage_events_headers):
        resp = self._post(
            api_client, manage_events_headers, "https://chat.whatsapp.com/AbcDef123456"
        )
        assert resp.status_code == 201

    def test_valid_wa_me_link(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "https://wa.me/14155551234")
        assert resp.status_code == 201

    def test_bare_whatsapp_domain_rejected(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "https://chat.whatsapp.com/")
        assert resp.status_code == 422

    def test_bare_whatsapp_domain_no_scheme_rejected(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "whatsapp.com")
        assert resp.status_code == 422

    def test_wrong_domain_rejected(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "https://example.com/some-path")
        assert resp.status_code == 422

    def test_empty_whatsapp_accepted(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "")
        assert resp.status_code == 201


@pytest.mark.django_db
class TestPartifulLinkValidation:
    def _post(self, api_client, headers, partiful_link):
        return api_client.post(
            "/api/community/events/",
            {**BASE_EVENT, "partiful_link": partiful_link},
            content_type="application/json",
            **headers,
        )

    def test_valid_partiful_event_link(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "https://partiful.com/e/abc123")
        assert resp.status_code == 201

    def test_bare_partiful_domain_rejected(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "https://partiful.com/")
        assert resp.status_code == 422

    def test_bare_partiful_no_scheme_rejected(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "partiful.com")
        assert resp.status_code == 422

    def test_wrong_domain_rejected(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "https://example.com/e/abc123")
        assert resp.status_code == 422

    def test_empty_partiful_accepted(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "")
        assert resp.status_code == 201


@pytest.mark.django_db
class TestOtherLinkValidation:
    def _post(self, api_client, headers, other_link):
        return api_client.post(
            "/api/community/events/",
            {**BASE_EVENT, "other_link": other_link},
            content_type="application/json",
            **headers,
        )

    def test_valid_https_link(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "https://example.com/some/page")
        assert resp.status_code == 201

    def test_bare_domain_accepted(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "https://example.com/")
        assert resp.status_code == 201
        assert resp.json()["other_link"] == "https://example.com/"

    def test_bare_domain_no_scheme_accepted_and_normalized(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "example.com")
        assert resp.status_code == 201
        assert resp.json()["other_link"] == "https://example.com"

    def test_empty_other_link_accepted(self, api_client, manage_events_headers):
        resp = self._post(api_client, manage_events_headers, "")
        assert resp.status_code == 201


@pytest.mark.django_db
class TestLinkValidationOnPatch:
    def _create_event(self, api_client, headers):
        resp = api_client.post(
            "/api/community/events/",
            BASE_EVENT,
            content_type="application/json",
            **headers,
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_patch_bare_partiful_rejected(self, api_client, manage_events_headers):
        event_id = self._create_event(api_client, manage_events_headers)
        resp = api_client.patch(
            f"/api/community/events/{event_id}/",
            {"partiful_link": "partiful.com"},
            content_type="application/json",
            **manage_events_headers,
        )
        assert resp.status_code == 422

    def test_patch_valid_partiful_accepted(self, api_client, manage_events_headers):
        event_id = self._create_event(api_client, manage_events_headers)
        resp = api_client.patch(
            f"/api/community/events/{event_id}/",
            {"partiful_link": "https://partiful.com/e/xyz789"},
            content_type="application/json",
            **manage_events_headers,
        )
        assert resp.status_code == 200

    def test_patch_empty_string_clears_link(self, api_client, manage_events_headers):
        """Empty string clears the link (sets it to blank), None means 'no change'."""
        event_id = self._create_event(api_client, manage_events_headers)
        resp = api_client.patch(
            f"/api/community/events/{event_id}/",
            {"partiful_link": ""},
            content_type="application/json",
            **manage_events_headers,
        )
        assert resp.status_code == 200
