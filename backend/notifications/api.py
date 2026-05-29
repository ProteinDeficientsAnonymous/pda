from uuid import UUID

from community._shared import ErrorOut
from community._validation import Code, raise_validation
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from ninja import Router
from ninja.responses import Status

from notifications.models import Notification, SseTicket
from notifications.schemas import NotificationOut, SseTicketOut, UnreadCountOut

router = Router()


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
def list_notifications(request):
    notifications = Notification.objects.filter(recipient=request.auth).order_by("-created_at")[:30]
    return Status(200, [_notification_out(n) for n in notifications])


@router.post("/sse-ticket/", response={200: SseTicketOut, 429: ErrorOut}, auth=gated_jwt)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def create_sse_ticket(request):
    """Mint a short-lived single-use ticket for opening the SSE stream.

    EventSource can't send an Authorization header, so the stream is opened
    with ?ticket=<opaque>. The ticket is bound to this user, expires in ~60s,
    and is consumed on first use — keeping the JWT itself out of the URL.
    """
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
