from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from contextlib import aclosing
from dataclasses import dataclass

import psycopg
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.http import JsonResponse, StreamingHttpResponse

from notifications.models import SseTicket

logger = logging.getLogger("pda")

_PG_CHANNEL = "notifications"
_EVENT_UPDATES_CHANNEL = "event_updates"
_HEARTBEAT_INTERVAL = 30  # seconds
_READ_PAYLOAD_PREFIX = "read:"


def notify_read_state_changed(user_id: str) -> None:
    """Tell the user's other tabs/devices their read state changed so they refetch."""
    if connection.vendor != "postgresql":
        return
    # Best-effort: the mark-read write already succeeded.
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT pg_notify('{_PG_CHANNEL}', %s)", [f"{_READ_PAYLOAD_PREFIX}{user_id}"]
            )
    except DatabaseError:
        logger.warning("read-state ping failed", exc_info=True)


# Each stream holds its own Postgres connection; cap anonymous ones per worker process.
MAX_ANONYMOUS_CONNECTIONS = 200
# Ends anonymous streams so the reconnect re-checks the rsvp token and event eligibility.
_ANONYMOUS_MAX_LIFETIME = 15 * 60  # seconds

_anonymous_lock = threading.Lock()
_anonymous_connections = 0


@dataclass(frozen=True)
class StreamScope:
    user_id: str | None
    event_id: str | None


@sync_to_async
def consume_ticket(ticket_str: str) -> StreamScope | None:
    """Atomically validate + consume a single-use SSE ticket.

    Row-locked (select_for_update) so concurrent connections can't both consume
    one ticket. Returns None for a missing/expired/used ticket.
    """
    with transaction.atomic():
        try:
            ticket = SseTicket.objects.select_for_update().get(token=ticket_str)
        except SseTicket.DoesNotExist:
            return None
        if ticket.used or ticket.is_expired:
            return None
        ticket.used = True
        ticket.save(update_fields=["used"])
    return StreamScope(
        user_id=str(ticket.user_id) if ticket.user_id else None,
        event_id=str(ticket.event_id) if ticket.event_id else None,
    )


def _anonymous_slots_full() -> bool:
    with _anonymous_lock:
        return _anonymous_connections >= MAX_ANONYMOUS_CONNECTIONS


def try_acquire_anonymous_slot() -> bool:
    """Reserve one of the capped anonymous-connection slots; False if full."""
    global _anonymous_connections
    with _anonymous_lock:
        if _anonymous_connections >= MAX_ANONYMOUS_CONNECTIONS:
            return False
        _anonymous_connections += 1
        return True


def release_anonymous_slot() -> None:
    global _anonymous_connections
    with _anonymous_lock:
        _anonymous_connections = max(0, _anonymous_connections - 1)


def _build_async_dsn() -> str:
    """Build a psycopg async DSN from Django's DATABASES config."""
    db = settings.DATABASES["default"]
    host = db.get("HOST", "localhost")
    port = db.get("PORT", 5432) or 5432
    return f"postgresql://{db['USER']}:{db['PASSWORD']}@{host}:{port}/{db['NAME']}"


def format_notify_for_user(channel: str, payload: str, scope: StreamScope) -> str | None:
    """Turn a pg_notify payload into an SSE frame for this stream, or None to skip."""
    if scope.user_id is None:
        return _format_notify_for_event(channel, payload, scope.event_id)
    if channel == _PG_CHANNEL:
        return _format_personal_notify(payload, scope.user_id)
    if channel == _EVENT_UPDATES_CHANNEL:
        # Payload format: "<user_id-or-*>:<event_id>". "*" broadcasts to every
        # connected viewer (used for changes visible to any member, e.g. comments).
        target_user, _, event_id = payload.partition(":")
        if target_user in (scope.user_id, "*") and event_id:
            return _event_updated_frame(event_id)
        return None
    return None


def _format_personal_notify(payload: str, user_id: str) -> str | None:
    if payload == user_id:
        return f"event: notification\ndata: {json.dumps({'type': 'notification'})}\n\n"
    if payload == f"{_READ_PAYLOAD_PREFIX}{user_id}":
        return "event: notifications_read\ndata: {}\n\n"
    return None


def _format_notify_for_event(channel: str, payload: str, event_id: str | None) -> str | None:
    """Anonymous streams only see wildcard pings for the one event their ticket was minted for."""
    if channel != _EVENT_UPDATES_CHANNEL or event_id is None:
        return None
    target_user, _, pinged_event_id = payload.partition(":")
    if target_user == "*" and pinged_event_id == event_id:
        return _event_updated_frame(event_id)
    return None


def _event_updated_frame(event_id: str) -> str:
    return f"event: event_updated\ndata: {json.dumps({'event_id': event_id})}\n\n"


async def sse_generator(scope: StreamScope):
    """Async generator that yields SSE events for a single connection."""
    if scope.user_id is not None:
        async for frame in _stream_frames(scope, deadline=None):
            yield frame
        return
    # Reserved here, not in the view, so the finally always pairs with it.
    if not try_acquire_anonymous_slot():
        return
    try:
        deadline = time.monotonic() + _ANONYMOUS_MAX_LIFETIME
        async for frame in _stream_frames(scope, deadline=deadline):
            yield frame
    finally:
        release_anonymous_slot()


async def _stream_frames(scope: StreamScope, *, deadline: float | None):
    try:
        dsn = _build_async_dsn()
        async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
            await conn.execute(f"LISTEN {_PG_CHANNEL}")
            await conn.execute(f"LISTEN {_EVENT_UPDATES_CHANNEL}")
            yield "event: connected\ndata: {}\n\n"

            # A timeout must not cancel notifies(): that closes the generator and ends the stream.
            while not conn.closed and (deadline is None or time.monotonic() < deadline):
                async with aclosing(conn.notifies(timeout=_HEARTBEAT_INTERVAL)) as notifies:
                    async for notify in notifies:
                        frame = format_notify_for_user(notify.channel, notify.payload, scope)
                        if frame is not None:
                            yield frame
                yield ": heartbeat\n\n"
    except asyncio.CancelledError:
        return
    except Exception:
        logger.exception("SSE stream error for user %s event %s", scope.user_id, scope.event_id)


async def notification_stream(request):
    """SSE endpoint — GET /api/notifications/stream/?ticket=<opaque>

    Auth is a single-use ticket (from POST /sse-ticket/), not the JWT, so the
    access token never appears in the URL.
    """
    db = settings.DATABASES.get("default", {})
    if "postgresql" not in db.get("ENGINE", ""):
        return JsonResponse({"detail": "SSE requires PostgreSQL"}, status=503)

    ticket = request.GET.get("ticket")
    if not ticket:
        return JsonResponse({"detail": "ticket required"}, status=401)

    scope = await consume_ticket(ticket)
    if scope is None:
        return JsonResponse({"detail": "invalid ticket"}, status=401)

    if scope.user_id is None and _anonymous_slots_full():
        return JsonResponse({"detail": "too many anonymous viewers"}, status=503)

    response = StreamingHttpResponse(
        sse_generator(scope),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
