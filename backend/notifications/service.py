from __future__ import annotations

from typing import TYPE_CHECKING

from .whatsapp import send_to_group

if TYPE_CHECKING:
    from collections.abc import Iterable

    from community.models import Event
    from users.models import User


def notify_new_event(event: Event) -> bool:
    lines = [f"📅 New event: *{event.title}*"]

    start = event.start_datetime.strftime("%A, %B %-d at %-I:%M %p")
    end = event.end_datetime.strftime("%-I:%M %p")
    lines.append(f"🕐 {start} – {end}")

    if event.location:
        lines.append(f"📍 {event.location}")

    if event.description:
        lines.append(f"\n{event.description}")

    if event.partiful_link:
        lines.append(f"\nRSVP: {event.partiful_link}")
    elif event.whatsapp_link:
        lines.append(f"\nChat: {event.whatsapp_link}")
    elif event.other_link:
        lines.append(f"\nMore info: {event.other_link}")

    return send_to_group("\n".join(lines))


def admin_broadcast(message: str) -> bool:
    return send_to_group(message)


def create_event_invite_notifications(
    event: Event,
    new_user_ids: Iterable[str],
    inviter: User,
) -> None:
    from notifications.models import Notification, NotificationType

    inviter_id = str(inviter.pk)
    inviter_name = inviter.display_name or inviter.phone_number
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=user_id,
                notification_type=NotificationType.EVENT_INVITE,
                event=event,
                message=f"{inviter_name} invited you to {event.title}",
            )
            for user_id in new_user_ids
            if str(user_id) != inviter_id
        ]
    )
