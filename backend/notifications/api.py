from uuid import UUID

from community._shared import ErrorOut, _optional_jwt
from community._validation import Code, raise_validation
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.contrib.auth.models import AnonymousUser
from ninja import Query, Router
from ninja.responses import Status

from notifications.models import Notification, SseTicket
from notifications.schemas import NotificationOut, SseTicketOut, UnreadCountOut

router = Router()

# Cap a single list page so callers can't request an unbounded slab.
MAX_LIST_LIMIT = 50
DEFAULT_LIST_LIMIT = 30


def _notification_out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=str(n.id),
        notification_type=n.notification_type,
        event_id=str(n.event_id) if n.event_id else None,  # ty: ignore[unresolved-attribute]
        related_user_id=str(n.related_user_id) if n.related_user_id else None,  # ty: ignore[unresolved-attribute]
        message=n.message,
        is_read=n.is_read,
        created_at=n.created_at,
    )


@router.get("/", response={200: list[NotificationOut]}, auth=gated_jwt)
def list_notifications(
    request,
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(0, ge=0),
):
    notifications = Notification.objects.filter(recipient=request.auth).order_by("-created_at")[
        offset : offset + limit
    ]
    return Status(200, [_notification_out(n) for n in notifications])


def _sse_ticket_rate_key(request) -> str:
    if isinstance(request.auth, AnonymousUser):
        return request.META.get("REMOTE_ADDR", "anon")
    return str(request.auth.pk)


@router.post("/sse-ticket/", response={200: SseTicketOut, 429: ErrorOut}, auth=_optional_jwt)
@rate_limit(key_func=_sse_ticket_rate_key, rate="30/m")
def create_sse_ticket(request):
    """Mint a short-lived single-use ticket for opening the SSE stream.

    Lets the client open the stream with ?ticket= instead of the JWT (EventSource
    can't send an auth header). Anonymous viewers get a ticket too, for public
    event pages' wildcard comment broadcasts.
    """
    if isinstance(request.auth, AnonymousUser):
        ticket = SseTicket.mint_anonymous()
    else:
        ticket = SseTicket.mint_for_user(request.auth)
    return Status(200, SseTicketOut(ticket=ticket.token))


@router.get("/unread-count/", response={200: UnreadCountOut}, auth=gated_jwt)
def unread_count(request):
    count = Notification.objects.filter(recipient=request.auth, is_read=False).count()
    return Status(200, UnreadCountOut(count=count))


@router.post("/read-all/", response={200: dict}, auth=gated_jwt)
def mark_all_read(request):
    Notification.objects.filter(recipient=request.auth, is_read=False).update(is_read=True)
    return Status(200, {"detail": "ok"})


@router.post("/{notification_id}/read/", response={200: dict, 404: ErrorOut}, auth=gated_jwt)
def mark_read(request, notification_id: UUID):
    updated = Notification.objects.filter(id=notification_id, recipient=request.auth).update(
        is_read=True
    )
    if not updated:
        raise_validation(Code.Notification.NOT_FOUND, status_code=404)
    return Status(200, {"detail": "ok"})
