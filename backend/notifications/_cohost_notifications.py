from __future__ import annotations

from typing import TYPE_CHECKING

from users._helpers import visible_display_name
from users.models import User

from notifications.models import Notification, NotificationType
from notifications.service import notify_users

if TYPE_CHECKING:
    from collections.abc import Iterable

    from community.models import Event


def create_cohost_invite_notifications(
    event: Event,
    new_user_ids: Iterable[str],
    invited_by: User,
) -> None:
    """Notify users who just received a co-host invite for this event."""
    invited_by_id = str(invited_by.pk)
    invited_by_name = visible_display_name(invited_by, None)
    notified_ids = [str(uid) for uid in new_user_ids if str(uid) != invited_by_id]
    if not notified_ids:
        return
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=user_id,
                notification_type=NotificationType.COHOST_INVITE,
                event=event,
                related_user=invited_by,
                message=(
                    f"{invited_by_name} invited you to co-host {event.title} — tap to respond"
                ),
            )
            for user_id in notified_ids
        ]
    )
    notify_users(notified_ids)


def create_cohost_invite_accepted_notification(
    event: Event,
    invitee: User,
    inviter_id: str | None,
) -> None:
    """Notify the inviter that an invitee accepted their co-host invite."""
    if inviter_id is None or str(inviter_id) == str(invitee.pk):
        return
    invitee_name = visible_display_name(invitee, None)
    Notification.objects.create(
        recipient_id=str(inviter_id),
        notification_type=NotificationType.COHOST_INVITE_ACCEPTED,
        event=event,
        related_user=invitee,
        message=f"{invitee_name} accepted your co-host invite for {event.title}",
    )
    notify_users([str(inviter_id)])


def create_cohost_invite_declined_notification(
    event: Event,
    invitee: User,
    inviter_id: str | None,
) -> None:
    """Notify the inviter that an invitee declined their co-host invite."""
    if inviter_id is None or str(inviter_id) == str(invitee.pk):
        return
    invitee_name = visible_display_name(invitee, None)
    Notification.objects.create(
        recipient_id=str(inviter_id),
        notification_type=NotificationType.COHOST_INVITE_DECLINED,
        event=event,
        related_user=invitee,
        message=f"{invitee_name} declined your co-host invite for {event.title}",
    )
    notify_users([str(inviter_id)])


def create_cohost_removed_notification(event: Event, removed_user: User, remover: User) -> None:
    """Notify a co-host that they've been removed from an event by someone else.

    Caller is responsible for skipping self-removal — no need to notify
    yourself that you stepped down.
    """
    if str(remover.pk) == str(removed_user.pk):
        return
    remover_name = visible_display_name(remover, None)
    Notification.objects.create(
        recipient_id=str(removed_user.pk),
        notification_type=NotificationType.COHOST_REMOVED,
        event=event,
        related_user=remover,
        message=f"{remover_name} removed you as a co-host of {event.title}",
    )
    notify_users([str(removed_user.pk)])
