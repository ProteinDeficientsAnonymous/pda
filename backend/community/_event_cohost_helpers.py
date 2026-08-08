from __future__ import annotations

from typing import TYPE_CHECKING

from config.media_proxy import media_path
from notifications._cohost_notifications import create_cohost_invite_notifications
from notifications.service import broadcast_cohost_change, create_event_invite_notifications
from users._helpers import visible_display_name
from users.models import User as UserModel

from community._cohost_invite_helpers import (
    diff_cohost_invites,
    get_pending_invites_for_event,
    send_cohost_invite_emails,
)
from community._event_schemas import PendingCoHostInviteOut
from community.models import Event

if TYPE_CHECKING:
    from collections.abc import Iterable


def _can_manage_cohost_invites(
    requesting_user,
    co_host_ids: set[str],
) -> bool:
    """Accepted co-hosts can see and rescind pending invites. Admins are
    intentionally excluded — this is a host-only workflow, not admin moderation."""
    if requesting_user is None:
        return False
    return str(requesting_user.pk) in co_host_ids


def _pending_cohost_invites_out(
    event: Event, auth_user, co_host_ids: set[str]
) -> list[PendingCoHostInviteOut]:
    if not _can_manage_cohost_invites(auth_user, co_host_ids):
        return []
    return [
        PendingCoHostInviteOut(
            id=str(inv.id),
            user_id=str(inv.user_id),
            user_name=visible_display_name(inv.user, auth_user),
            user_photo_url=media_path(inv.user.profile_photo),
            invited_at=inv.invited_at,
        )
        for inv in get_pending_invites_for_event(event)
    ]


def _update_co_hosts(
    event: Event,
    co_host_ids: Iterable[str],
    updater: UserModel,
) -> None:
    """Reconcile cohost invites against the requested ids and broadcast updates.

    With the invite-approval flow, this no longer mutates ``event.co_hosts``
    directly for newly-added users — those go to ``EventCoHostInvite`` as
    PENDING and only land in ``event.co_hosts`` once accepted. Removals still
    take effect immediately (the rescind helper drops them from
    ``event.co_hosts`` if they had been accepted).
    """
    next_ids = {str(uid) for uid in co_host_ids}
    newly_invited, removed_accepted_ids = diff_cohost_invites(event, next_ids, updater)
    if newly_invited:
        create_cohost_invite_notifications(event, newly_invited, updater)
        send_cohost_invite_emails(event, newly_invited, updater)

    if newly_invited or removed_accepted_ids:
        broadcast_cohost_change(
            event,
            exclude_user_ids={str(updater.pk)},
            extra_user_ids=set(newly_invited) | set(removed_accepted_ids),
        )


def _update_invited_users(
    event: Event,
    invited_user_ids: Iterable[str],
    inviter: UserModel,
) -> None:
    """Update event.invited_users and notify newly added users."""
    id_list = list(invited_user_ids)
    old_ids = set(event.invited_users.values_list("pk", flat=True))
    invited = UserModel.objects.filter(pk__in=id_list)
    event.invited_users.set(invited)
    new_ids = {str(uid) for uid in id_list} - {str(uid) for uid in old_ids}
    if new_ids:
        create_event_invite_notifications(event, new_ids, inviter)
