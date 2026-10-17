"""Tests for GatedJWTAuth — per-request enforcement of account state.

A valid JWT outlives the state changes that should revoke access (unusable
password, pause, archive). GatedJWTAuth re-checks on every protected request and
403s, except for the allowlist a pending user needs to resolve their state.

OptionalJWTAuth uses the same checks: a blocked token is anonymous on reads and
403s on writes.
"""

from datetime import timedelta

import pytest
from community.models import Event, EventComment, EventRSVP, RSVPStatus
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role


def _headers(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}  # type: ignore


@pytest.mark.django_db
class TestGatedJWTAuth:
    def test_needs_password_reset_blocks_protected_endpoint(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550301", password="pass", first_name="Reset", last_name="Me"
        )
        user.needs_password_reset = True
        user.save(update_fields=["needs_password_reset"])

        # A normal protected endpoint (not on the allowlist) → 403.
        resp = api_client.get("/api/notifications/", **_headers(user))
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == "auth.password_reset_required"

    def test_needs_password_reset_allows_me(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550302", password="pass", first_name="Reset", last_name="Me"
        )
        user.needs_password_reset = True
        user.save(update_fields=["needs_password_reset"])

        # /me/ is allowlisted so the frontend can read the flag and route.
        resp = api_client.get("/api/auth/me/", **_headers(user))
        assert resp.status_code == 200
        assert resp.json()["needs_password_reset"] is True

    def test_needs_password_reset_allows_complete_onboarding(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550303",
            password="pass",
            first_name="Reset",
            last_name="Me",
            email="reset@example.com",
        )
        user.needs_password_reset = True
        user.set_unusable_password()
        user.save(update_fields=["needs_password_reset", "password"])

        # The escape hatch must stay reachable.
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={"new_password": "FreshPass123!"},
            content_type="application/json",
            **_headers(user),
        )
        assert resp.status_code == 200, resp.content
        user.refresh_from_db()
        assert user.needs_password_reset is False

    def test_needs_onboarding_blocks_protected_endpoint(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550304",
            password="pass",
            first_name="",
            last_name="",
            needs_onboarding=True,
        )
        resp = api_client.get("/api/notifications/", **_headers(user))
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == "auth.onboarding_required"

    def test_paused_user_blocked_on_protected_endpoint_after_token_issued(self, api_client):
        """is_paused set AFTER a token was issued must still revoke access per-request."""
        user = User.objects.create_user(
            phone_number="+12025550305", password="pass", first_name="Paused", last_name=""
        )
        headers = _headers(user)  # token minted while active
        user.is_paused = True
        user.save(update_fields=["is_paused"])

        resp = api_client.get("/api/notifications/", **headers)
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == "auth.account_paused"

    def test_archived_user_blocked_on_protected_endpoint_after_token_issued(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550306", password="pass", first_name="Archived", last_name=""
        )
        headers = _headers(user)
        user.archived_at = timezone.now()
        user.save(update_fields=["archived_at"])

        resp = api_client.get("/api/notifications/", **headers)
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == "auth.account_archived"

    def test_normal_user_unaffected(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550307", password="pass", first_name="Normal", last_name=""
        )
        resp = api_client.get("/api/notifications/", **_headers(user))
        assert resp.status_code == 200

    def test_needs_guidelines_consent_blocks_protected_endpoint(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550308", password="pass", first_name="No", last_name="Consent"
        )
        # Opt back into the gated state (conftest stamps consent by default).
        user.guidelines_consent_at = None
        user.save(update_fields=["guidelines_consent_at"])

        resp = api_client.get("/api/notifications/", **_headers(user))
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == "auth.guidelines_consent_required"

    def test_needs_guidelines_consent_allows_me(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550309", password="pass", first_name="No", last_name="Consent"
        )
        user.guidelines_consent_at = None
        user.save(update_fields=["guidelines_consent_at"])

        # /me/ is allowlisted so the frontend can read the flag and route.
        resp = api_client.get("/api/auth/me/", **_headers(user))
        assert resp.status_code == 200
        assert resp.json()["needs_guidelines_consent"] is True

    def test_needs_guidelines_consent_allows_accept_endpoint(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550310", password="pass", first_name="No", last_name="Consent"
        )
        user.guidelines_consent_at = None
        user.save(update_fields=["guidelines_consent_at"])

        # The escape hatch must stay reachable while gated.
        resp = api_client.post(
            "/api/auth/accept-consents/",
            data={"consent_types": ["guidelines"]},
            content_type="application/json",
            **_headers(user),
        )
        assert resp.status_code == 200, resp.content

    def test_password_reset_takes_priority_over_consent(self, api_client):
        """A user owing both a password and consent is sent to the password gate first."""
        user = User.objects.create_user(
            phone_number="+12025550311", password="pass", first_name="Both", last_name=""
        )
        user.needs_password_reset = True
        user.guidelines_consent_at = None
        user.save(update_fields=["needs_password_reset", "guidelines_consent_at"])

        resp = api_client.get("/api/notifications/", **_headers(user))
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == "auth.password_reset_required"


_BLOCK_CODES = {
    "paused": "auth.account_paused",
    "archived": "auth.account_archived",
    "needs_password_reset": "auth.password_reset_required",
}

_BLOCK_PHONES = {
    "paused": "+12025550321",
    "archived": "+12025550322",
    "needs_password_reset": "+12025550323",
}


def _block_user(user, block: str) -> None:
    if block == "paused":
        user.is_paused = True
        user.save(update_fields=["is_paused"])
        return
    if block == "archived":
        user.archived_at = timezone.now()
        user.save(update_fields=["archived_at"])
        return
    user.needs_password_reset = True
    user.save(update_fields=["needs_password_reset"])


def _public_event(creator):
    return Event.objects.create(
        title="Optional gate",
        start_datetime=timezone.now() + timedelta(days=7),
        whatsapp_link="https://chat.whatsapp.com/abc",
        created_by=creator,
    )


def _rsvp_viewer(phone: str, event):
    viewer = User.objects.create_user(phone_number=phone, password="pass", first_name="Viewer")
    EventRSVP.objects.create(event=event, user=viewer, status=RSVPStatus.ATTENDING)
    return viewer


@pytest.mark.django_db
class TestOptionalJWTAccountState:
    @pytest.mark.parametrize("block", ["paused", "archived", "needs_password_reset"])
    def test_event_detail_blocked_token_matches_logged_out(self, api_client, test_user, block):
        event = _public_event(test_user)
        viewer = _rsvp_viewer(_BLOCK_PHONES[block], event)
        headers = _headers(viewer)
        _block_user(viewer, block)

        url = f"/api/community/events/{event.id}/"
        anon = api_client.get(url)
        blocked = api_client.get(url, **headers)

        assert anon.status_code == 200
        assert blocked.status_code == 200
        assert blocked.json()["whatsapp_link"] == ""
        assert blocked.json()["guests"] == []
        assert blocked.json() == anon.json()

    @pytest.mark.parametrize("block", ["paused", "archived", "needs_password_reset"])
    def test_comment_post_blocked_token_forbidden(self, api_client, test_user, block):
        event = _public_event(test_user)
        viewer = _rsvp_viewer(_BLOCK_PHONES[block], event)
        headers = _headers(viewer)
        _block_user(viewer, block)

        resp = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            data={"body": "should not land"},
            content_type="application/json",
            **headers,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == _BLOCK_CODES[block]
        assert not EventComment.objects.filter(event=event).exists()

    def test_archived_manage_events_delete_comment_forbidden(self, api_client, test_user):
        event = _public_event(test_user)
        comment = EventComment.objects.create(event=event, author=test_user, body="keep me")
        manager = User.objects.create_user(
            phone_number="+12025550324", password="pass", first_name="Archived", last_name="Manager"
        )
        role = Role.objects.create(
            name="optional_jwt_event_manager", permissions=[PermissionKey.MANAGE_EVENTS]
        )
        manager.roles.add(role)
        headers = _headers(manager)
        _block_user(manager, "archived")

        resp = api_client.delete(
            f"/api/community/events/{event.id}/comments/{comment.id}/",
            **headers,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == "auth.account_archived"
        comment.refresh_from_db()
        assert comment.deleted_at is None

    def test_active_rsvp_event_detail_shows_member_fields(self, api_client, test_user):
        event = _public_event(test_user)
        viewer = _rsvp_viewer("+12025550325", event)

        resp = api_client.get(f"/api/community/events/{event.id}/", **_headers(viewer))
        assert resp.status_code == 200
        body = resp.json()
        assert body["whatsapp_link"] == "https://chat.whatsapp.com/abc"
        assert any(guest["user_id"] == str(viewer.id) for guest in body["guests"])
