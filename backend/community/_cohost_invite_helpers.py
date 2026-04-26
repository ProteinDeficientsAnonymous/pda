"""Co-host invite helpers — diffing user input against existing invites,
plus lazy-on-read expiration of pending invites past the event end.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from community._validation import Code, raise_validation
from community.models import CoHostInviteStatus, Event, EventCoHostInvite

if TYPE_CHECKING:
    from collections.abc import Iterable

    from users.models import User as UserModel


def expire_stale_cohost_invites(event: Event) -> None:
    """Flip PENDING invites to EXPIRED once the event has ended.

    Called from any read path that returns invite data so the UI never sees
    actionable invites for a past event.

    TODO(#382): replace this lazy-on-read approach with a scheduled job that
    sweeps stale invites once.
    """
    end = event.end_datetime
    if end is None or end >= timezone.now():
        return
    EventCoHostInvite.objects.filter(event=event, status=CoHostInviteStatus.PENDING).update(
        status=CoHostInviteStatus.EXPIRED, decided_at=timezone.now()
    )


_ACTIVE_OR_PENDING = (CoHostInviteStatus.PENDING, CoHostInviteStatus.ACCEPTED)


def _upsert_pending_invite(
    event: Event,
    user_id: str,
    inviter: UserModel,
    existing: EventCoHostInvite | None,
) -> bool:
    """Create or flip a row to PENDING for ``user_id``. Returns True if newly invited."""
    if existing is None:
        EventCoHostInvite.objects.create(
            event=event,
            user_id=user_id,
            invited_by=inviter,
            status=CoHostInviteStatus.PENDING,
        )
        return True
    if existing.status in _ACTIVE_OR_PENDING:
        return False
    existing.status = CoHostInviteStatus.PENDING
    existing.invited_by = inviter
    existing.decided_at = None
    existing.save(update_fields=["status", "invited_by", "decided_at"])
    return True


def _rescind_invite(invite: EventCoHostInvite) -> bool:
    """Flip a PENDING/ACCEPTED invite to RESCINDED. Returns True if it was ACCEPTED
    (so the caller knows to remove the user from ``event.co_hosts``)."""
    if invite.status not in _ACTIVE_OR_PENDING:
        return False
    was_accepted = invite.status == CoHostInviteStatus.ACCEPTED
    invite.status = CoHostInviteStatus.RESCINDED
    invite.decided_at = timezone.now()
    invite.save(update_fields=["status", "decided_at"])
    return was_accepted


def diff_cohost_invites(
    event: Event,
    co_host_ids: Iterable[str],
    inviter: UserModel,
) -> tuple[list[str], list[str]]:
    """Reconcile event.co_hosts + cohost_invites against the requested co-host id list.

    For each requested id:
      - no existing invite → create PENDING
      - existing PENDING / ACCEPTED → noop
      - existing DECLINED / RESCINDED / EXPIRED → flip to PENDING
        (clear decided_at; treat as a fresh invite)

    For ids removed from the list:
      - PENDING → flip to RESCINDED
      - ACCEPTED → flip to RESCINDED AND remove from event.co_hosts

    Returns ``(newly_invited_user_ids, ids_removed_from_event_co_hosts)`` so the
    caller can fire notifications and trigger live-update broadcasts.

    `event.co_hosts` continues to mean "users who have an ACCEPTED invite". It
    is not touched directly except to remove a user when their accepted invite
    is rescinded by the inviter.

    The event creator is silently filtered out of the requested ids — they're
    already a host and don't need a co-host invite for their own event.

    Raises ``Code.CoHostInvite.EVENT_IS_PAST`` if the input would create or
    revive a pending invite on a past event. Removals continue to work — the
    host can still trim the roster after the fact.
    """
    next_ids = _next_ids_excluding_creator(event, co_host_ids)
    existing_by_user = {str(inv.user_id): inv for inv in event.cohost_invites.all()}
    _check_past_event_guard(event, next_ids, existing_by_user)

    newly_invited: list[str] = []
    accepted_co_host_ids_to_remove: list[str] = []

    with transaction.atomic():
        for user_id in next_ids:
            if _upsert_pending_invite(event, user_id, inviter, existing_by_user.get(user_id)):
                newly_invited.append(user_id)
        for user_id, invite in existing_by_user.items():
            if user_id in next_ids:
                continue
            if _rescind_invite(invite):
                accepted_co_host_ids_to_remove.append(user_id)
        if accepted_co_host_ids_to_remove:
            event.co_hosts.remove(*accepted_co_host_ids_to_remove)

    return newly_invited, accepted_co_host_ids_to_remove


def _next_ids_excluding_creator(event: Event, co_host_ids: Iterable[str]) -> set[str]:
    """Normalize requested ids and drop the creator (they're already a host)."""
    next_ids = {str(uid) for uid in co_host_ids}
    if event.created_by_id is not None:
        next_ids.discard(str(event.created_by_id))
    return next_ids


def _check_past_event_guard(
    event: Event,
    next_ids: set[str],
    existing_by_user: dict[str, EventCoHostInvite],
) -> None:
    """Raise EVENT_IS_PAST if any requested id would create or revive an invite.

    Mirrors the logic in ``_upsert_pending_invite`` — a request is "upsert-y"
    if there's no existing row, or there is one but it's in a non-active state
    (declined / rescinded / expired / removed) that would get flipped back to
    pending. Removals are unaffected; the guard is a no-op for those.
    """
    if not event.is_past:
        return
    for user_id in next_ids:
        existing = existing_by_user.get(user_id)
        if existing is None or existing.status not in _ACTIVE_OR_PENDING:
            raise_validation(Code.CoHostInvite.EVENT_IS_PAST, status_code=400)


def get_pending_invites_for_event(event: Event) -> list[EventCoHostInvite]:
    """Return the event's pending invites after running lazy expiration.

    Caller must have already verified the viewer is allowed to see them.
    """
    expire_stale_cohost_invites(event)
    return list(
        EventCoHostInvite.objects.filter(
            event=event, status=CoHostInviteStatus.PENDING
        ).select_related("user")
    )


def get_my_pending_invite(event: Event, user) -> EventCoHostInvite | None:
    """Return the requesting user's PENDING invite for this event, or None."""
    if user is None:
        return None
    expire_stale_cohost_invites(event)
    return EventCoHostInvite.objects.filter(
        event=event, user=user, status=CoHostInviteStatus.PENDING
    ).first()


def has_pending_cohost_invite(event: Event, user) -> bool:
    """Cheap EXISTS check used by the draft visibility gate.

    Without this, a pending cohost invitee would 404 on the draft they were
    invited to and never get to the accept/decline banner.
    """
    if user is None:
        return False
    expire_stale_cohost_invites(event)
    return EventCoHostInvite.objects.filter(
        event=event, user=user, status=CoHostInviteStatus.PENDING
    ).exists()
