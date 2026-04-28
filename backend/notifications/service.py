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


def broadcast_cohost_change(
    event: Event,
    *,
    exclude_user_ids: Iterable[str] = (),
    extra_user_ids: Iterable[str] = (),
) -> None:
    """Live-update ping scoped to creator + accepted co-hosts.

    Used when the cohost roster changes (accept / decline / rescind) so
    the host-management UI refreshes for the people who care, without
    pinging every member who's RSVP'd or been invited to the event.
    """
    recipients: set[str] = set()
    if event.created_by_id:
        recipients.add(str(event.created_by_id))
    recipients.update(str(uid) for uid in event.co_hosts.values_list("pk", flat=True))
    recipients.update(str(uid) for uid in extra_user_ids)
    recipients.difference_update(str(uid) for uid in exclude_user_ids)
    if recipients:
        _ping_event_update(recipients, str(event.pk))


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


def create_cohost_invite_notifications(
    event: Event,
    new_user_ids: Iterable[str],
    invited_by: User,
) -> None:
    """Notify users who just received a co-host invite for this event."""
    from notifications.models import Notification, NotificationType

    invited_by_id = str(invited_by.pk)
    invited_by_name = invited_by.display_name or invited_by.phone_number
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
    _notify_users(notified_ids)


def create_cohost_invite_accepted_notification(
    event: Event,
    invitee: User,
    inviter_id: str | None,
) -> None:
    """Notify the inviter that an invitee accepted their co-host invite."""
    from notifications.models import Notification, NotificationType

    if inviter_id is None or str(inviter_id) == str(invitee.pk):
        return
    invitee_name = invitee.display_name or invitee.phone_number
    Notification.objects.create(
        recipient_id=str(inviter_id),
        notification_type=NotificationType.COHOST_INVITE_ACCEPTED,
        event=event,
        related_user=invitee,
        message=f"{invitee_name} accepted your co-host invite for {event.title}",
    )
    _notify_users([str(inviter_id)])


def create_cohost_invite_declined_notification(
    event: Event,
    invitee: User,
    inviter_id: str | None,
) -> None:
    """Notify the inviter that an invitee declined their co-host invite."""
    from notifications.models import Notification, NotificationType

    if inviter_id is None or str(inviter_id) == str(invitee.pk):
        return
    invitee_name = invitee.display_name or invitee.phone_number
    Notification.objects.create(
        recipient_id=str(inviter_id),
        notification_type=NotificationType.COHOST_INVITE_DECLINED,
        event=event,
        related_user=invitee,
        message=f"{invitee_name} declined your co-host invite for {event.title}",
    )
    _notify_users([str(inviter_id)])


def create_cohost_removed_notification(event: Event, removed_user: User, remover: User) -> None:
    """Notify a co-host that they've been removed from an event by someone else.

    Caller is responsible for skipping self-removal — no need to notify
    yourself that you stepped down.
    """
    from notifications.models import Notification, NotificationType

    if str(remover.pk) == str(removed_user.pk):
        return
    remover_name = remover.display_name or remover.phone_number
    Notification.objects.create(
        recipient_id=str(removed_user.pk),
        notification_type=NotificationType.COHOST_REMOVED,
        event=event,
        related_user=remover,
        message=f"{remover_name} removed you as a co-host of {event.title}",
    )
    _notify_users([str(removed_user.pk)])


def create_text_blast_failures_notification(event: Event, sender: User, failure_count: int) -> None:
    """Tell the host that some recipients didn't get their blast.

    Fired only when at least one delivery in a blast failed at the Twilio
    layer (invalid number, carrier rejection, rate limit, etc.). The host
    can drill into the blast detail screen to see per-recipient errors.
    """
    from notifications.models import Notification, NotificationType

    if failure_count <= 0:
        return
    plural = "person" if failure_count == 1 else "people"
    Notification.objects.create(
        recipient_id=str(sender.pk),
        notification_type=NotificationType.TEXT_BLAST_FAILURES,
        event=event,
        message=f"text blast for {event.title}: {failure_count} {plural} didn't get it",
    )
    _notify_users([str(sender.pk)])


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
