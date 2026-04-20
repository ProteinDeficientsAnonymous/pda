from uuid import UUID

from community._shared import ErrorOut
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth

from notifications.models import Notification
from notifications.schemas import NotificationOut, UnreadCountOut

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


@router.get("/", response={200: list[NotificationOut]}, auth=JWTAuth())
def list_notifications(request):
    notifications = Notification.objects.filter(recipient=request.auth).order_by("-created_at")[:30]
    return Status(200, [_notification_out(n) for n in notifications])


@router.get("/unread-count/", response={200: UnreadCountOut}, auth=JWTAuth())
def unread_count(request):
    count = Notification.objects.filter(recipient=request.auth, is_read=False).count()
    return Status(200, UnreadCountOut(count=count))


@router.post("/read-all/", response={200: dict}, auth=JWTAuth())
def mark_all_read(request):
    Notification.objects.filter(recipient=request.auth, is_read=False).update(is_read=True)
    return Status(200, {"detail": "ok"})


@router.post("/{notification_id}/read/", response={200: dict, 404: ErrorOut}, auth=JWTAuth())
def mark_read(request, notification_id: UUID):
    updated = Notification.objects.filter(id=notification_id, recipient=request.auth).update(
        is_read=True
    )
    if not updated:
        return Status(404, ErrorOut(detail="Notification not found."))
    return Status(200, {"detail": "ok"})
