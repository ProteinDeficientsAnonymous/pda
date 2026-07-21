from __future__ import annotations

import asyncio
import json
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import JsonResponse, StreamingHttpResponse

logger = logging.getLogger("pda")

_PG_CHANNEL = "notifications"
_EVENT_UPDATES_CHANNEL = "event_updates"
_HEARTBEAT_INTERVAL = 30  # seconds


_ANONYMOUS = "anonymous"


@sync_to_async
def _consume_ticket(ticket_str: str) -> AbstractBaseUser | str | None:
    """Atomically validate + consume a single-use SSE ticket.

    Row-locked (select_for_update) so concurrent connections can't both consume
    one ticket. Returns the ticket's user, the sentinel string `_ANONYMOUS` for
    an anonymous ticket (no user attached), or None for a missing/expired/used
    ticket or one whose user has since been deleted.
    """
    from django.db import transaction

    from notifications.models import SseTicket

    with transaction.atomic():
        try:
            ticket = SseTicket.objects.select_for_update().get(token=ticket_str)
        except SseTicket.DoesNotExist:
            return None
        if ticket.used or ticket.is_expired:
            return None
        ticket.used = True
        ticket.save(update_fields=["used"])
        user_id = ticket.user_id
    if user_id is None:
        return _ANONYMOUS
    User = get_user_model()
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


def _build_async_dsn() -> str:
    """Build a psycopg async DSN from Django's DATABASES config."""
    db = settings.DATABASES["default"]
    host = db.get("HOST", "localhost")
    port = db.get("PORT", 5432) or 5432
    return f"postgresql://{db['USER']}:{db['PASSWORD']}@{host}:{port}/{db['NAME']}"


def _format_notify_for_user(channel: str, payload: str, user_id: str | None) -> str | None:
    """Turn a pg_notify payload into an SSE frame for this user, or None to skip.

    `user_id` is None for an anonymous viewer — they can never own a personal
    notification, only see wildcard event-comment broadcasts.
    """
    if channel == _PG_CHANNEL:
        if user_id is not None and payload == user_id:
            return f"event: notification\ndata: {json.dumps({'type': 'notification'})}\n\n"
        return None
    if channel == _EVENT_UPDATES_CHANNEL:
        # Payload format: "<user_id-or-*>:<event_id>". "*" broadcasts to every
        # connected viewer (used for changes visible to any member, e.g. comments).
        target_user, _, event_id = payload.partition(":")
        if (target_user == "*" or (user_id is not None and target_user == user_id)) and event_id:
            return f"event: event_updated\ndata: {json.dumps({'event_id': event_id})}\n\n"
        return None
    return None


async def _sse_generator(user_id: str | None):
    """Async generator that yields SSE events for a single connection."""
    # lazy import: psycopg only needed for the postgres LISTEN path
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

    Auth is a single-use ticket (from POST /sse-ticket/), not the JWT, so the
    access token never appears in the URL.
    """
    db = settings.DATABASES.get("default", {})
    if "postgresql" not in db.get("ENGINE", ""):
        return JsonResponse({"detail": "SSE requires PostgreSQL"}, status=503)

    ticket = request.GET.get("ticket")
    if not ticket:
        return JsonResponse({"detail": "ticket required"}, status=401)

    consumed = await _consume_ticket(ticket)
    if consumed is None:
        return JsonResponse({"detail": "invalid ticket"}, status=401)
    user_id = None if consumed == _ANONYMOUS else str(consumed.pk)

    response = StreamingHttpResponse(
        _sse_generator(user_id),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
