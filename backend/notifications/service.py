from __future__ import annotations

from typing import TYPE_CHECKING

from .whatsapp import send_to_group

if TYPE_CHECKING:
    from collections.abc import Iterable

    from community.models import Event
    from users.models import User


def _notify_users(user_ids: Iterable[str]) -> None:
    """Fire pg_notify for each recipient so SSE clients get immediate updates."""
    from django.db import connection

    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        for uid in user_ids:
            cursor.execute("SELECT pg_notify('notifications', %s)", [str(uid)])


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


def create_join_request_notifications(display_name: str) -> None:
    from django.db.models import Q
    from users.models import User
    from users.permissions import PermissionKey

    from notifications.models import Notification, NotificationType

    recipients = User.objects.filter(
        Q(roles__name="admin", roles__is_default=True)
        | Q(roles__permissions__contains=PermissionKey.APPROVE_JOIN_REQUESTS)
    ).distinct()

    Notification.objects.bulk_create(
        [
            Notification(
                recipient=user,
                notification_type=NotificationType.JOIN_REQUEST,
                message=f"new join request from {display_name}",
            )
            for user in recipients
        ]
    )
    _notify_users(str(user.pk) for user in recipients)


def create_magic_link_request_notifications(user: User) -> None:
    from django.db.models import Q
    from users.models import User as UserModel
    from users.permissions import PermissionKey

    from notifications.models import Notification, NotificationType

    display = user.display_name or user.phone_number
    recipients = UserModel.objects.filter(
        Q(roles__name="admin", roles__is_default=True)
        | Q(roles__permissions__contains=PermissionKey.APPROVE_JOIN_REQUESTS)
    ).distinct()

    Notification.objects.bulk_create(
        [
            Notification(
                recipient=recipient,
                notification_type=NotificationType.MAGIC_LINK_REQUEST,
                related_user=user,
                message=f"{display} requested a new login link",
            )
            for recipient in recipients
        ]
    )
    _notify_users(str(recipient.pk) for recipient in recipients)


def create_cohost_added_notifications(
    event: Event,
    new_user_ids: Iterable[str],
    added_by: User,
) -> None:
    from notifications.models import Notification, NotificationType

    added_by_id = str(added_by.pk)
    added_by_name = added_by.display_name or added_by.phone_number
    notified_ids = [uid for uid in new_user_ids if str(uid) != added_by_id]
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=user_id,
                notification_type=NotificationType.COHOST_ADDED,
                event=event,
                message=f"{added_by_name} added you as a co-host for {event.title}",
            )
            for user_id in notified_ids
        ]
    )
    _notify_users(notified_ids)


def create_event_cancellation_notifications(event: Event, canceller: User) -> None:
    from community.models import RSVPStatus

    from notifications.models import Notification, NotificationType

    canceller_id = str(canceller.pk)
    invited_ids = {str(u.pk) for u in event.invited_users.all()}
    rsvp_ids = {str(r.user_id) for r in event.rsvps.all() if r.status == RSVPStatus.ATTENDING}
    recipient_ids = list((invited_ids | rsvp_ids) - {canceller_id})
    if not recipient_ids:
        return
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=user_id,
                notification_type=NotificationType.EVENT_CANCELLED,
                event=event,
                message=f"{event.title} was cancelled",
            )
            for user_id in recipient_ids
        ]
    )
    _notify_users(recipient_ids)


def create_event_invite_notifications(
    event: Event,
    new_user_ids: Iterable[str],
    inviter: User,
) -> None:
    from notifications.models import Notification, NotificationType

    inviter_id = str(inviter.pk)
    inviter_name = inviter.display_name or inviter.phone_number
    notified_ids = [uid for uid in new_user_ids if str(uid) != inviter_id]
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=user_id,
                notification_type=NotificationType.EVENT_INVITE,
                event=event,
                message=f"{inviter_name} invited you to {event.title}",
            )
            for user_id in notified_ids
        ]
    )
    _notify_users(notified_ids)
