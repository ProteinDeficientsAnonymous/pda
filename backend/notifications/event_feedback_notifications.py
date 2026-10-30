from __future__ import annotations

from typing import TYPE_CHECKING

from notifications.models import Notification, NotificationType
from notifications.service import _event_recipient_ids, notify_users

if TYPE_CHECKING:
    from community.models import Event

_MESSAGE_MAX_LENGTH = Notification._meta.get_field("message").max_length or 255


def notify_event_feedback(event: Event) -> None:
    """Ping the event's host + co-hosts that an anonymous feedback response arrived."""
    recipient_ids = _event_recipient_ids(event, exclude="")
    if not recipient_ids:
        return
    message = f"new feedback for {event.title}"[:_MESSAGE_MAX_LENGTH]
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=rid,
                notification_type=NotificationType.EVENT_FEEDBACK,
                event=event,
                message=message,
            )
            for rid in recipient_ids
        ]
    )
    notify_users(recipient_ids)
