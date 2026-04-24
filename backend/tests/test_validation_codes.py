"""End-to-end tests for machine-readable validation errors.

Validators now raise ``ValidationException(code, field)`` instead of
``ValueError("free text")``. The global Ninja handler reshapes both those
and stock Pydantic errors into ``{ detail: [{code, field, params?}, ...] }``
so the frontend owns UI copy.
"""

import pytest
from community._validation import Code

from tests.conftest import future_iso


def base_event() -> dict:
    return {
        "title": "Validation Test Event",
        "start_datetime": future_iso(days=30),
    }


@pytest.fixture
def manage_events_headers(db):
    from ninja_jwt.tokens import RefreshToken
    from users.models import User
    from users.permissions import PermissionKey
    from users.roles import Role

    user = User.objects.create_user(
        phone_number="+14155559010",
        password="validationcodepass123",
        display_name="Validation Codes Manager",
    )
    role = Role.objects.create(name="val_mgr", permissions=[PermissionKey.MANAGE_EVENTS])
    user.roles.add(role)
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestValidationCodesShape:
    def test_start_datetime_missing_returns_code_and_field(self, api_client, manage_events_headers):
        payload = {"title": "No date"}  # missing start_datetime, not tbd, not draft
        resp = api_client.post(
            "/api/community/events/",
            payload,
            content_type="application/json",
            **manage_events_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert isinstance(detail, list)
        assert any(
            e["code"] == Code.Event.START_DATETIME_REQUIRED_UNLESS_TBD
            and e["field"] == "start_datetime"
            for e in detail
        )
        # Defensive: no Pydantic-flavored strings leak through.
        for e in detail:
            assert "msg" not in e
            assert not any("Value error" in str(v) for v in e.values())

    def test_draft_without_start_datetime_is_allowed(self, api_client, manage_events_headers):
        payload = {"title": "Draft no date", "status": "draft"}
        resp = api_client.post(
            "/api/community/events/",
            payload,
            content_type="application/json",
            **manage_events_headers,
        )
        assert resp.status_code == 201

    def test_invalid_whatsapp_host_returns_code_with_field(self, api_client, manage_events_headers):
        resp = api_client.post(
            "/api/community/events/",
            {**base_event(), "whatsapp_link": "https://notwhatsapp.com/x"},
            content_type="application/json",
            **manage_events_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        match = next(e for e in detail if e["code"] == Code.Url.WHATSAPP_NOT_RECOGNIZED)
        assert match["field"] == "whatsapp_link"
        assert "allowed_hosts" in match["params"]

    def test_bare_whatsapp_domain_returns_url_path_required(
        self, api_client, manage_events_headers
    ):
        resp = api_client.post(
            "/api/community/events/",
            {**base_event(), "whatsapp_link": "https://chat.whatsapp.com/"},
            content_type="application/json",
            **manage_events_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any(
            e["code"] == Code.Url.PATH_REQUIRED and e["field"] == "whatsapp_link" for e in detail
        )

    def test_generic_pydantic_error_gets_fallback_code(self, api_client, manage_events_headers):
        # max_attendees expects int | None — a string triggers a default
        # Pydantic type error, not one of our Code namespaces.
        resp = api_client.post(
            "/api/community/events/",
            {**base_event(), "max_attendees": "not a number"},
            content_type="application/json",
            **manage_events_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any(e["code"] == "field_invalid" for e in detail)

    def test_missing_title_gets_field_required(self, api_client, manage_events_headers):
        resp = api_client.post(
            "/api/community/events/",
            {"start_datetime": future_iso(days=30)},
            content_type="application/json",
            **manage_events_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any(e["code"] == "field_required" and e["field"] == "title" for e in detail)
