"""Tests for the SSE notification stream endpoint + its single-use ticket flow."""

import asyncio
from datetime import timedelta

import psycopg
import pytest
from asgiref.sync import async_to_sync
from community.models import Event, EventRSVP, EventType, PageVisibility, RSVPStatus
from django.conf import settings
from django.core.cache import caches
from django.utils import timezone
from ninja_jwt.tokens import AccessToken, RefreshToken
from notifications import sse
from notifications.models import SseTicket
from notifications.sse import (
    _MAX_ANONYMOUS_CONNECTIONS,
    _consume_ticket,
    _format_notify_for_user,
    _release_anonymous_slot,
    _sse_generator,
    _StreamScope,
    _try_acquire_anonymous_slot,
)
from users.models import NonMemberRsvpToken, User

from tests.conftest import future_iso

_MEMBER = _StreamScope(user_id="user-2", event_id=None)
_ANON_EVENT_1 = _StreamScope(user_id=None, event_id="event-1")


@pytest.mark.django_db
class TestFormatNotifyForUser:
    def test_event_update_matches_target_user(self):
        frame = _format_notify_for_user("event_updates", "user-2:event-1", _MEMBER)
        assert frame is not None
        assert "event: event_updated" in frame

    def test_event_update_skips_other_user(self):
        assert _format_notify_for_user("event_updates", "user-1:event-1", _MEMBER) is None

    def test_event_update_wildcard_matches_any_user(self):
        frame = _format_notify_for_user("event_updates", "*:event-1", _MEMBER)
        assert frame is not None
        assert "event: event_updated" in frame

    def test_anonymous_gets_wildcard_for_its_event(self):
        frame = _format_notify_for_user("event_updates", "*:event-1", _ANON_EVENT_1)
        assert frame is not None
        assert '"event_id": "event-1"' in frame

    def test_anonymous_skips_wildcard_for_other_event(self):
        assert _format_notify_for_user("event_updates", "*:event-2", _ANON_EVENT_1) is None

    def test_anonymous_skips_targeted_ping_for_its_event(self):
        assert _format_notify_for_user("event_updates", "user-1:event-1", _ANON_EVENT_1) is None

    def test_personal_notification_never_matches_anonymous(self):
        assert _format_notify_for_user("notifications", "user-1", _ANON_EVENT_1) is None

    def test_unscoped_anonymous_gets_nothing(self):
        scope = _StreamScope(user_id=None, event_id=None)
        assert _format_notify_for_user("event_updates", "*:event-1", scope) is None


@pytest.mark.django_db
class TestAnonymousConnectionCap:
    @pytest.fixture(autouse=True)
    def _reset_counter(self, monkeypatch):
        monkeypatch.setattr(sse, "_anonymous_connections", 0)

    def test_acquire_fails_once_at_capacity(self):
        for _ in range(_MAX_ANONYMOUS_CONNECTIONS):
            assert _try_acquire_anonymous_slot() is True
        assert _try_acquire_anonymous_slot() is False

    def test_release_frees_a_slot_for_reuse(self):
        for _ in range(_MAX_ANONYMOUS_CONNECTIONS):
            assert _try_acquire_anonymous_slot() is True
        _release_anonymous_slot()
        assert _try_acquire_anonymous_slot() is True

    def test_release_never_goes_negative(self):
        _release_anonymous_slot()
        _release_anonymous_slot()
        for _ in range(_MAX_ANONYMOUS_CONNECTIONS):
            assert _try_acquire_anonymous_slot() is True
        assert _try_acquire_anonymous_slot() is False

    def test_generator_yields_nothing_when_full(self, monkeypatch):
        monkeypatch.setattr(sse, "_anonymous_connections", _MAX_ANONYMOUS_CONNECTIONS)

        async def drain():
            return [frame async for frame in _sse_generator(_ANON_EVENT_1)]

        assert async_to_sync(drain)() == []
        assert sse._anonymous_connections == _MAX_ANONYMOUS_CONNECTIONS

    def test_generator_releases_slot_after_stream_error(self, monkeypatch):
        def broken_dsn():
            raise RuntimeError("no db")

        monkeypatch.setattr(sse, "_build_async_dsn", broken_dsn)

        async def drain():
            return [frame async for frame in _sse_generator(_ANON_EVENT_1)]

        assert async_to_sync(drain)() == []
        assert sse._anonymous_connections == 0


def _auth_headers(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():

    caches["ratelimit"].clear()
    yield
    caches["ratelimit"].clear()


@pytest.mark.django_db
class TestSseTicketMint:
    def test_mint_returns_ticket(self, test_user, api_client):
        response = api_client.post("/api/notifications/sse-ticket/", **_auth_headers(test_user))
        assert response.status_code == 200
        assert response.json()["ticket"]

    def test_minted_ticket_is_bound_to_user(self, test_user, api_client):

        response = api_client.post("/api/notifications/sse-ticket/", **_auth_headers(test_user))
        token = response.json()["ticket"]
        ticket = SseTicket.objects.get(token=token)
        assert ticket.user_id == test_user.pk
        assert ticket.used is False

    def test_mint_without_auth_or_event_returns_401(self, api_client):
        response = api_client.post("/api/notifications/sse-ticket/")
        assert response.status_code == 401

    def test_expired_bearer_returns_401_not_anonymous_ticket(self, test_user, api_client):
        access = AccessToken.for_user(test_user)
        access.set_exp(lifetime=-timedelta(minutes=1))
        response = api_client.post(
            "/api/notifications/sse-ticket/", HTTP_AUTHORIZATION=f"Bearer {access}"
        )
        assert response.status_code == 401
        assert not SseTicket.objects.exists()

    def test_paused_user_returns_403(self, test_user, api_client):
        test_user.is_paused = True
        test_user.save(update_fields=["is_paused"])
        response = api_client.post("/api/notifications/sse-ticket/", **_auth_headers(test_user))
        assert response.status_code == 403
        assert not SseTicket.objects.exists()


@pytest.fixture
def public_event(db, test_user):
    return Event.objects.create(
        title="Public Event",
        start_datetime=future_iso(days=30),
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        rsvp_enabled=True,
        created_by=test_user,
    )


@pytest.fixture
def non_member(db):
    user = User.objects.create_user(
        phone_number="+12025550188",
        first_name="Non",
        last_name="Member",
        is_member=False,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def rsvp_token(non_member):
    return NonMemberRsvpToken.issue(non_member).token


def _mint_anonymous(api_client, event, token):
    return api_client.post(
        f"/api/notifications/sse-ticket/?event_id={event.id}&token={token}",
    )


@pytest.mark.django_db
class TestAnonymousSseTicketMint:
    def test_rsvpd_non_member_gets_event_scoped_ticket(
        self, api_client, public_event, non_member, rsvp_token
    ):
        EventRSVP.objects.create(event=public_event, user=non_member, status=RSVPStatus.ATTENDING)
        response = _mint_anonymous(api_client, public_event, rsvp_token)
        assert response.status_code == 200, response.content
        ticket = SseTicket.objects.get(token=response.json()["ticket"])
        assert ticket.user_id is None
        assert ticket.event_id == public_event.id

    def test_token_without_rsvp_on_event_returns_404(self, api_client, public_event, rsvp_token):
        response = _mint_anonymous(api_client, public_event, rsvp_token)
        assert response.status_code == 404
        assert not SseTicket.objects.exists()

    def test_invalid_token_returns_404(self, api_client, public_event):
        response = _mint_anonymous(api_client, public_event, "garbage")
        assert response.status_code == 404

    def test_members_only_event_returns_404(self, api_client, public_event, non_member, rsvp_token):
        EventRSVP.objects.create(event=public_event, user=non_member, status=RSVPStatus.ATTENDING)
        public_event.visibility = PageVisibility.MEMBERS_ONLY
        public_event.save(update_fields=["visibility"])
        response = _mint_anonymous(api_client, public_event, rsvp_token)
        assert response.status_code == 404
        assert not SseTicket.objects.exists()

    def test_member_bearer_ignores_event_scope(self, test_user, api_client, public_event):
        response = api_client.post(
            f"/api/notifications/sse-ticket/?event_id={public_event.id}",
            **_auth_headers(test_user),
        )
        assert response.status_code == 200
        ticket = SseTicket.objects.get(token=response.json()["ticket"])
        assert ticket.user_id == test_user.pk
        assert ticket.event_id is None


@pytest.mark.django_db
class TestConsumeTicket:
    def test_user_ticket_scope(self, test_user):
        ticket = SseTicket.mint_for_user(test_user)
        scope = async_to_sync(_consume_ticket)(ticket.token)
        assert scope == _StreamScope(user_id=str(test_user.pk), event_id=None)

    def test_event_ticket_scope(self, public_event):
        ticket = SseTicket.mint_for_event(public_event)
        scope = async_to_sync(_consume_ticket)(ticket.token)
        assert scope == _StreamScope(user_id=None, event_id=str(public_event.pk))

    def test_second_consume_is_rejected(self, public_event):
        ticket = SseTicket.mint_for_event(public_event)
        assert async_to_sync(_consume_ticket)(ticket.token) is not None
        assert async_to_sync(_consume_ticket)(ticket.token) is None


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

        ticket = SseTicket.mint_for_user(test_user)
        response = api_client.get(f"/api/notifications/stream/?ticket={ticket.token}")
        assert response.status_code != 401

    def test_ticket_is_single_use(self, test_user, api_client):

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

        ticket = SseTicket.objects.create(
            token="expired-ticket-token",
            user=test_user,
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        response = api_client.get(f"/api/notifications/stream/?ticket={ticket.token}")
        assert response.status_code == 401
        assert response.json()["detail"] == "invalid ticket"


@pytest.mark.skipif(
    "postgresql" not in settings.DATABASES["default"]["ENGINE"],
    reason="LISTEN/NOTIFY requires PostgreSQL",
)
@pytest.mark.django_db
class TestSseStreamLoop:
    def test_stream_delivers_notify_after_heartbeat(self, monkeypatch):
        monkeypatch.setattr(sse, "_HEARTBEAT_INTERVAL", 0.2)

        async def run() -> list[str]:
            stream = sse._sse_generator(_StreamScope(user_id="user-1", event_id=None))
            try:
                frames = [
                    await asyncio.wait_for(anext(stream), timeout=5),
                    await asyncio.wait_for(anext(stream), timeout=5),
                ]
                async with await psycopg.AsyncConnection.connect(
                    sse._build_async_dsn(), autocommit=True
                ) as notifier:
                    await notifier.execute("SELECT pg_notify('notifications', 'user-1')")
                while not frames[-1].startswith("event: notification"):
                    frames.append(await asyncio.wait_for(anext(stream), timeout=5))
                return frames
            finally:
                await stream.aclose()

        frames = asyncio.run(run())
        assert frames[0].startswith("event: connected")
        assert frames[1] == ": heartbeat\n\n"
        assert frames[-1].startswith("event: notification")
