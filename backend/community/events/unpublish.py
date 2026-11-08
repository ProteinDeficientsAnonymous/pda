from django.db import transaction
from notifications.models import Notification, NotificationType
from notifications.service import broadcast_event_created, notify_users

from community.models import Event


def clear_unpublished_side_effects(event: Event) -> None:
    """Drop the in-app invites of an event just moved to DRAFT and ping live views after commit."""
    # Republish re-creates these via _notify_new_invitees; sent invite emails can't be recalled.
    invites = Notification.objects.filter(
        event=event, notification_type=NotificationType.EVENT_INVITE
    )
    invitee_ids = [str(uid) for uid in invites.values_list("recipient_id", flat=True)]
    invites.delete()
    # Live calendars and the invite bell stay stale unless we ping after commit.
    transaction.on_commit(lambda: broadcast_event_created(event))
    if invitee_ids:
        transaction.on_commit(lambda: notify_users(invitee_ids))
