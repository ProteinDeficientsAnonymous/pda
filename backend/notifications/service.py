from __future__ import annotations

from typing import TYPE_CHECKING

from .whatsapp import send_to_group

if TYPE_CHECKING:
    from collections.abc import Iterable

    from community.models import Event
    from users.models import User


def _notify_users(user_ids: Iterable[str]) -> None:
    """Fire pg_notify on the notifications channel (for new notification rows)."""
    from django.db import connection

    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        for uid in user_ids:
            cursor.execute("SELECT pg_notify('notifications', %s)", [str(uid)])


_EVENT_UPDATES_CHANNEL = "event_updates"


def _ping_event_update(user_ids: Iterable[str], event_id: str) -> None:
    """Fire pg_notify on the event_updates channel — a silent live-update ping.

    The SSE layer delivers this as an `event_updated` event (distinct from
    `notification`) so the frontend only invalidates event caches — no bell,
    no unread-count refetch, no notification row.
    """
    from django.db import connection

    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        for uid in user_ids:
            payload = f"{uid}:{event_id}"
            cursor.execute(f"SELECT pg_notify('{_EVENT_UPDATES_CHANNEL}', %s)", [payload])


def broadcast_event_update(
    event: Event,
    *,
    exclude_user_ids: Iterable[str] = (),
    extra_user_ids: Iterable[str] = (),
) -> None:
    """Live-update ping for everyone currently able to see this event.

    Creates no notification rows. Stakeholders are the creator + current
    co-hosts + invited + attending/maybe RSVPs. Pass `extra_user_ids` to
    include users who just lost their stake (e.g. a co-host who was removed).
    """
    from community.models import RSVPStatus

    recipients: set[str] = set()
    if event.created_by_id:
        recipients.add(str(event.created_by_id))
    recipients.update(str(uid) for uid in event.co_hosts.values_list("pk", flat=True))
    recipients.update(str(uid) for uid in event.invited_users.values_list("pk", flat=True))
    recipients.update(
        str(r.user_id)
        for r in event.rsvps.all()
        if r.status in (RSVPStatus.ATTENDING, RSVPStatus.MAYBE)
    )
    recipients.update(str(uid) for uid in extra_user_ids)
    recipients.difference_update(str(uid) for uid in exclude_user_ids)
    if recipients:
        _ping_event_update(recipients, str(event.pk))


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


def create_event_flag_notifications(event: Event, flagger: User) -> None:
    from django.db.models import Q
    from users.models import User as UserModel
    from users.permissions import PermissionKey

    from notifications.models import Notification, NotificationType

    flagger_name = flagger.display_name or flagger.phone_number
    recipients = UserModel.objects.filter(
        Q(roles__name="admin", roles__is_default=True)
        | Q(roles__permissions__contains=PermissionKey.MANAGE_EVENTS)
    ).distinct()

    Notification.objects.bulk_create(
        [
            Notification(
                recipient=user,
                notification_type=NotificationType.EVENT_FLAGGED,
                event=event,
                message=f"{flagger_name} flagged '{event.title}'",
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
    rsvp_ids = {
        str(r.user_id)
        for r in event.rsvps.all()
        if r.status in (RSVPStatus.ATTENDING, RSVPStatus.MAYBE)
    }
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


def create_waitlist_promoted_notifications(
    event: Event,
    promoted_user_ids: Iterable[str],
) -> None:
    from notifications.models import Notification, NotificationType

    user_ids = list(promoted_user_ids)
    if not user_ids:
        return
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=user_id,
                notification_type=NotificationType.WAITLIST_PROMOTED,
                event=event,
                message=f"a spot opened up — you're going to {event.title}!",
            )
            for user_id in user_ids
        ]
    )
    _notify_users(user_ids)
