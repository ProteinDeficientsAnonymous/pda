"""Tests for the SSE notification stream endpoint + its single-use ticket flow."""

from datetime import timedelta

import pytest
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from notifications.sse import _format_notify_for_user


class TestFormatNotifyForUser:
    def test_event_update_matches_target_user(self):
        frame = _format_notify_for_user("event_updates", "user-1:event-1", "user-1")
        assert frame is not None
        assert "event: event_updated" in frame

    def test_event_update_skips_other_user(self):
        assert _format_notify_for_user("event_updates", "user-1:event-1", "user-2") is None

    def test_event_update_wildcard_matches_any_user(self):
        frame = _format_notify_for_user("event_updates", "*:event-1", "user-2")
        assert frame is not None
        assert "event: event_updated" in frame

    def test_event_update_wildcard_matches_anonymous_viewer(self):
        frame = _format_notify_for_user("event_updates", "*:event-1", None)
        assert frame is not None
        assert "event: event_updated" in frame

    def test_personal_notification_never_matches_anonymous_viewer(self):
        assert _format_notify_for_user("notifications", "user-1", None) is None


def _auth_headers(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestSseTicketMint:
    def test_mint_returns_ticket(self, test_user, api_client):
        response = api_client.post("/api/notifications/sse-ticket/", **_auth_headers(test_user))
        assert response.status_code == 200
        assert response.json()["ticket"]

    def test_minted_ticket_is_bound_to_user(self, test_user, api_client):
        from notifications.models import SseTicket

        response = api_client.post("/api/notifications/sse-ticket/", **_auth_headers(test_user))
        token = response.json()["ticket"]
        ticket = SseTicket.objects.get(token=token)
        assert ticket.user_id == test_user.pk
        assert ticket.used is False

    def test_anonymous_mint_returns_ticket(self, api_client):
        response = api_client.post("/api/notifications/sse-ticket/")
        assert response.status_code == 200
        assert response.json()["ticket"]

    def test_anonymous_ticket_has_no_user(self, api_client):
        from notifications.models import SseTicket

        response = api_client.post("/api/notifications/sse-ticket/")
        token = response.json()["ticket"]
        ticket = SseTicket.objects.get(token=token)
        assert ticket.user_id is None


@pytest.mark.django_db
class TestSseStreamAuth:
    def test_missing_ticket_returns_401(self, api_client):
        response = api_client.get("/api/notifications/stream/")
        assert response.status_code == 401
        assert response.json()["detail"] == "ticket required"

    def test_invalid_ticket_returns_401(self, api_client):
        response = api_client.get("/api/notifications/stream/?ticket=garbage")
        assert response.status_code == 401
        assert response.json()["detail"] == "invalid ticket"

    def test_jwt_in_query_no_longer_works(self, test_user, api_client):
        """Regression guard: the old ?token=<jwt> path must not authenticate."""
        token = str(RefreshToken.for_user(test_user).access_token)  # ty: ignore[unresolved-attribute]
        response = api_client.get(f"/api/notifications/stream/?token={token}")
        assert response.status_code == 401

    def test_valid_ticket_does_not_get_401(self, test_user, api_client):
        """A valid ticket passes auth — endpoint may return 200 (streaming) or
        fail for infra reasons (PG connect), but must not return 401."""
        from notifications.models import SseTicket

        ticket = SseTicket.mint_for_user(test_user)
        response = api_client.get(f"/api/notifications/stream/?ticket={ticket.token}")
        assert response.status_code != 401

    def test_ticket_is_single_use(self, test_user, api_client):
        from notifications.models import SseTicket

        ticket = SseTicket.mint_for_user(test_user)
        first = api_client.get(f"/api/notifications/stream/?ticket={ticket.token}")
        assert first.status_code != 401
        # Consuming the same ticket again is rejected.
        ticket.refresh_from_db()
        assert ticket.used is True
        second = api_client.get(f"/api/notifications/stream/?ticket={ticket.token}")
        assert second.status_code == 401
        assert second.json()["detail"] == "invalid ticket"

    def test_expired_ticket_returns_401(self, test_user, api_client):
        from notifications.models import SseTicket

        ticket = SseTicket.objects.create(
            token="expired-ticket-token",
            user=test_user,
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        response = api_client.get(f"/api/notifications/stream/?ticket={ticket.token}")
        assert response.status_code == 401
        assert response.json()["detail"] == "invalid ticket"
