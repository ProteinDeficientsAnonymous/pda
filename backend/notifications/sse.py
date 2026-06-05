from __future__ import annotations

import asyncio
import json
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import JsonResponse, StreamingHttpResponse

logger = logging.getLogger("pda")

_PG_CHANNEL = "notifications"
_EVENT_UPDATES_CHANNEL = "event_updates"
_HEARTBEAT_INTERVAL = 30  # seconds


@sync_to_async
def _consume_ticket(ticket_str: str) -> AbstractBaseUser | None:
    """Atomically validate + consume a single-use SSE ticket, return its user.

    Locks the ticket row (select_for_update) so two concurrent connections
    can't both consume the same ticket. Returns None for missing, expired,
    or already-used tickets — those are expected, not errors. Unexpected
    failures propagate so they surface in logs rather than masquerading as
    "invalid ticket".
    """
    from django.db import transaction

    from notifications.models import SseTicket

    with transaction.atomic():
        try:
            # select_related the user so the row lock and user load are a single
            # query (mirrors _consume_magic_token) — avoids a second round-trip
            # per stream open on the connect/reconnect hot path.
            ticket = (
                SseTicket.objects.select_for_update().select_related("user").get(token=ticket_str)
            )
        except SseTicket.DoesNotExist:
            return None
        if ticket.used or ticket.is_expired:
            return None
        ticket.used = True
        ticket.save(update_fields=["used"])
        return ticket.user


def _build_async_dsn() -> str:
    """Build a psycopg async DSN from Django's DATABASES config."""
    db = settings.DATABASES["default"]
    host = db.get("HOST", "localhost")
    port = db.get("PORT", 5432) or 5432
    return f"postgresql://{db['USER']}:{db['PASSWORD']}@{host}:{port}/{db['NAME']}"


def _format_notify_for_user(channel: str, payload: str, user_id: str) -> str | None:
    """Turn a pg_notify payload into an SSE frame for this user, or None to skip."""
    if channel == _PG_CHANNEL:
        if payload == user_id:
            return f"event: notification\ndata: {json.dumps({'type': 'notification'})}\n\n"
        return None
    if channel == _EVENT_UPDATES_CHANNEL:
        # Payload format: "<user_id>:<event_id>"
        target_user, _, event_id = payload.partition(":")
        if target_user == user_id and event_id:
            return f"event: event_updated\ndata: {json.dumps({'event_id': event_id})}\n\n"
        return None
    return None


async def _sse_generator(user_id: str):
    """Async generator that yields SSE events for a single user."""
    import psycopg

    dsn = _build_async_dsn()
    try:
        async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
            await conn.execute(f"LISTEN {_PG_CHANNEL}")
            await conn.execute(f"LISTEN {_EVENT_UPDATES_CHANNEL}")
            yield "event: connected\ndata: {}\n\n"

            gen = conn.notifies().__aiter__()
            while True:
                try:
                    notify = await asyncio.wait_for(gen.__anext__(), timeout=_HEARTBEAT_INTERVAL)
                    frame = _format_notify_for_user(notify.channel, notify.payload, user_id)
                    if frame is not None:
                        yield frame
                except TimeoutError:
                    yield ": heartbeat\n\n"
                except StopAsyncIteration:
                    break
    except asyncio.CancelledError:
        return
    except Exception:
        logger.exception("SSE stream error for user %s", user_id)


async def notification_stream(request):
    """SSE endpoint — GET /api/notifications/stream/?ticket=<opaque>

    Auth uses a short-lived single-use ticket (minted by POST
    /api/notifications/sse-ticket/) rather than the JWT, so the access token
    never appears in the URL (and thus not in logs / Referer / history).
    """
    db = settings.DATABASES.get("default", {})
    if "postgresql" not in db.get("ENGINE", ""):
        return JsonResponse({"detail": "SSE requires PostgreSQL"}, status=503)

    ticket = request.GET.get("ticket")
    if not ticket:
        return JsonResponse({"detail": "ticket required"}, status=401)

    user = await _consume_ticket(ticket)
    if user is None:
        return JsonResponse({"detail": "invalid ticket"}, status=401)

    response = StreamingHttpResponse(
        _sse_generator(str(user.pk)),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
