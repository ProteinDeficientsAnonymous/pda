from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from community.models import PageVisibility, RSVPStatus
from django.db import DatabaseError, connection
from users._helpers import visible_display_name
from users.models import User
from users.permissions import PermissionKey

from notifications.models import Notification, NotificationType

if TYPE_CHECKING:
    from collections.abc import Iterable

    from community.models import Event


def _notify_users(user_ids: Iterable[str]) -> None:
    """Fire pg_notify on the notifications channel (for new notification rows)."""
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
    if connection.vendor != "postgresql":
        return

    # Best-effort: the caller's write has already committed, so a pg_notify
    # failure here must not surface as a 500 for a request that succeeded.
    try:
        with connection.cursor() as cursor:
            for uid in user_ids:
                payload = f"{uid}:{event_id}"
                cursor.execute(f"SELECT pg_notify('{_EVENT_UPDATES_CHANNEL}', %s)", [payload])
    except DatabaseError:
        logging.getLogger(__name__).warning("event_update ping failed", exc_info=True)


def broadcast_event_comment_update(event: Event) -> None:
    """Live-update ping for anyone who can view this event's comments.

    Comments are readable by any member who can see the event, not just
    RSVP'd/invited stakeholders, so this pings every connected viewer for
    public/members-only events. Invite-only events stay scoped to the people
    who can actually see them, matching `broadcast_event_update`.
    """
    if event.visibility == PageVisibility.INVITE_ONLY:
        broadcast_event_update(event)
        return
    _ping_event_update(["*"], str(event.pk))


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
    recipients.update(str(c.pk) for c in event.co_hosts.all())
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
    recipients: set[str] = set()
    if event.created_by_id:
        recipients.add(str(event.created_by_id))
    recipients.update(str(c.pk) for c in event.co_hosts.all())
    recipients.update(str(u.pk) for u in event.invited_users.all())
    recipients.update(
        str(r.user_id)
        for r in event.rsvps.all()
        if r.status in (RSVPStatus.ATTENDING, RSVPStatus.MAYBE)
    )
    recipients.update(str(uid) for uid in extra_user_ids)
    recipients.difference_update(str(uid) for uid in exclude_user_ids)
    if recipients:
        _ping_event_update(recipients, str(event.pk))


def create_join_request_notifications(full_name: str) -> None:
    recipients = User.objects.with_permission(PermissionKey.APPROVE_JOIN_REQUESTS)

    Notification.objects.bulk_create(
        [
            Notification(
                recipient=user,
                notification_type=NotificationType.JOIN_REQUEST,
                message=f"new join request from {full_name}",
            )
            for user in recipients
        ]
    )
    _notify_users(str(user.pk) for user in recipients)


def create_event_flag_notifications(event: Event, flagger: User) -> None:
    flagger_name = flagger.full_name or flagger.phone_number
    recipients = User.objects.with_permission(PermissionKey.MANAGE_EVENTS)

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
    display = user.full_name or user.phone_number
    recipients = User.objects.with_permission(PermissionKey.MANAGE_USERS)

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
    _notify_users(notified_ids)


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
    _notify_users([str(inviter_id)])


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
    _notify_users([str(inviter_id)])


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
    _notify_users([str(removed_user.pk)])


def create_event_cancellation_notifications(event: Event, canceller: User) -> None:
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
    inviter_id = str(inviter.pk)
    inviter_name = visible_display_name(inviter, None)
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


def notify_comment_reply(reply) -> None:
    """Notify the parent comment's author that someone replied to them.

    No-op if `reply` is a top-level comment or if the replier is the
    parent's author.
    """
    if reply.parent_id is None:
        return
    parent_author_id = reply.parent.author_id
    if str(parent_author_id) == str(reply.author_id):
        return
    replier_name = visible_display_name(reply.author, None)
    event_title = reply.event.title
    Notification.objects.create(
        recipient_id=parent_author_id,
        notification_type=NotificationType.COMMENT_REPLY,
        event=reply.event,
        related_user=reply.author,
        message=f"{replier_name} replied to your comment on {event_title}",
    )
    _notify_users([str(parent_author_id)])


def _event_recipient_ids(event, *, exclude: str) -> list[str]:
    """Host + co-hosts, excluding `exclude` (usually the actor triggering the notification)."""
    recipient_ids: set[str] = set()
    if event.created_by_id is not None:
        recipient_ids.add(str(event.created_by_id))
    recipient_ids.update(str(u.pk) for u in event.co_hosts.all())
    recipient_ids.discard(exclude)
    return sorted(recipient_ids)


def notify_rsvp_declined_note(event, author, note: str) -> None:
    """Notify host + co-hosts that someone who can't go left a note. Ephemeral: not stored elsewhere."""
    recipient_id_list = _event_recipient_ids(event, exclude=str(author.pk))
    if not recipient_id_list:
        return
    name = visible_display_name(author, None)
    # Truncate the note (not the finished string) so the closing quote always survives — max_length=255.
    wrapper_len = len(f"{name} can't go: “”")
    max_note_len = max(0, 255 - wrapper_len)
    truncated_note = note if len(note) <= max_note_len else note[: max(0, max_note_len - 1)] + "…"
    message = f"{name} can't go: “{truncated_note}”"
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=rid,
                notification_type=NotificationType.RSVP_DECLINED_NOTE,
                event=event,
                related_user=author,
                message=message,
            )
            for rid in recipient_id_list
        ]
    )
    _notify_users(recipient_id_list)


def notify_checkin_reminder(event: Event) -> None:
    """Notify creator + co-hosts that a club/official event just started — go check people in."""
    recipient_id_list = _event_recipient_ids(event, exclude="")
    if not recipient_id_list:
        return
    message = f"{event.title} just started — head to check-in to check people in."
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=rid,
                notification_type=NotificationType.CHECKIN_NUDGE,
                event=event,
                message=message,
            )
            for rid in recipient_id_list
        ]
    )
    _notify_users(recipient_id_list)


def notify_event_comment(comment) -> None:
    """Notify event creator + co-hosts when someone posts a top-level comment. No-op for replies."""
    if comment.parent_id is not None:
        return
    event = comment.event
    recipient_id_list = _event_recipient_ids(event, exclude=str(comment.author_id))
    if not recipient_id_list:
        return
    commenter_name = visible_display_name(comment.author, None)
    message = f"{commenter_name} commented on {event.title}"
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=rid,
                notification_type=NotificationType.EVENT_COMMENT,
                event=event,
                related_user=comment.author,
                message=message,
            )
            for rid in recipient_id_list
        ]
    )
    _notify_users(recipient_id_list)
