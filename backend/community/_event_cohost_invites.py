"""Co-host invite endpoints — accept / decline / rescind / remove-cohost.

The DELETE endpoint covers both flows once an invite exists:
 - PENDING: rescind by a host (matches the original invite-flow design).
 - ACCEPTED: remove an accepted co-host. Either the host (kicks them) or the
   co-host themselves (steps down). A last-host guard blocks self-step-down
   when no creator + this is the only accepted co-host.
"""

from uuid import UUID

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from notifications.service import (
    broadcast_cohost_change,
    create_cohost_invite_accepted_notification,
    create_cohost_invite_declined_notification,
    create_cohost_removed_notification,
)

from community._cohost_invite_helpers import expire_stale_cohost_invites
from community._event_helpers import _can_manage_cohost_invites, _event_out
from community._event_schemas import EventOut
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import CoHostInviteStatus, Event, EventCoHostInvite

router = Router()


def _get_invite_or_404(event_id: UUID, invite_id: UUID) -> EventCoHostInvite:
    return get_object_or_404(
        EventCoHostInvite.objects.select_related("event", "user", "invited_by"),
        id=invite_id,
        event_id=event_id,
    )


def _reload_event_for_response(event_id: UUID) -> Event:
    return (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user", "cohost_invites__user")
        .get(id=event_id)
    )


@router.post(
    "/events/{event_id}/cohost-invites/{invite_id}/accept/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def accept_cohost_invite(request, event_id: UUID, invite_id: UUID):
    invite = _get_invite_or_404(event_id, invite_id)
    expire_stale_cohost_invites(invite.event)
    invite.refresh_from_db()

    if invite.user_id != request.auth.pk:
        raise_validation(Code.CoHostInvite.NOT_INVITEE, status_code=403)
    if invite.status != CoHostInviteStatus.PENDING:
        raise_validation(Code.CoHostInvite.NOT_PENDING, status_code=400)

    inviter_id = str(invite.invited_by_id) if invite.invited_by_id else None
    with transaction.atomic():
        invite.status = CoHostInviteStatus.ACCEPTED
        invite.decided_at = timezone.now()
        invite.save(update_fields=["status", "decided_at"])
        invite.event.co_hosts.add(invite.user)

    create_cohost_invite_accepted_notification(invite.event, invite.user, inviter_id)

    event = _reload_event_for_response(event_id)
    broadcast_cohost_change(event, exclude_user_ids={str(request.auth.pk)})
    return Status(200, _event_out(event, request.auth))


@router.post(
    "/events/{event_id}/cohost-invites/{invite_id}/decline/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def decline_cohost_invite(request, event_id: UUID, invite_id: UUID):
    invite = _get_invite_or_404(event_id, invite_id)
    expire_stale_cohost_invites(invite.event)
    invite.refresh_from_db()

    if invite.user_id != request.auth.pk:
        raise_validation(Code.CoHostInvite.NOT_INVITEE, status_code=403)
    if invite.status != CoHostInviteStatus.PENDING:
        raise_validation(Code.CoHostInvite.NOT_PENDING, status_code=400)

    inviter_id = str(invite.invited_by_id) if invite.invited_by_id else None
    invite.status = CoHostInviteStatus.DECLINED
    invite.decided_at = timezone.now()
    invite.save(update_fields=["status", "decided_at"])

    create_cohost_invite_declined_notification(invite.event, invite.user, inviter_id)

    event = _reload_event_for_response(event_id)
    return Status(200, _event_out(event, request.auth))


def _would_leave_event_hostless(event: Event, removing_user_id: str) -> bool:
    """True if removing this user would leave the event with zero hosts.

    The creator is a host. If they're set, removing any co-host is fine. If
    they're None (e.g. SET_NULL after deletion) and we'd be removing the only
    accepted co-host, refuse — the event needs at least one host.
    """
    if event.created_by_id is not None:
        return False
    co_host_ids = {str(uid) for uid in event.co_hosts.values_list("pk", flat=True)}
    return co_host_ids == {str(removing_user_id)}


def _rescind_pending(invite: EventCoHostInvite, is_host: bool) -> None:
    if not is_host:
        raise_validation(Code.CoHostInvite.NOT_HOST, status_code=403)
    invite.status = CoHostInviteStatus.RESCINDED
    invite.decided_at = timezone.now()
    invite.save(update_fields=["status", "decided_at"])


def _remove_accepted(invite: EventCoHostInvite, requester, is_host: bool, is_self: bool) -> None:
    if not (is_host or is_self):
        raise_validation(Code.CoHostInvite.NOT_HOST, status_code=403)
    event = invite.event
    if is_self and _would_leave_event_hostless(event, str(invite.user_id)):
        raise_validation(Code.CoHostInvite.WOULD_LEAVE_HOSTLESS, status_code=400)
    with transaction.atomic():
        invite.status = CoHostInviteStatus.REMOVED
        invite.decided_at = timezone.now()
        invite.save(update_fields=["status", "decided_at"])
        event.co_hosts.remove(invite.user)
    if not is_self:
        create_cohost_removed_notification(event, invite.user, requester)


@router.delete(
    "/events/{event_id}/cohost-invites/{invite_id}/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def rescind_cohost_invite(request, event_id: UUID, invite_id: UUID):
    """Rescind a pending invite OR remove an accepted co-host.

    PENDING → host-only, flips to RESCINDED.
    ACCEPTED → host or the co-host themselves, flips to REMOVED and drops
    the user from event.co_hosts. Blocks self-step-down that would leave
    the event without any host.
    Other statuses (DECLINED / RESCINDED / EXPIRED / REMOVED) → 400.
    """
    invite = _get_invite_or_404(event_id, invite_id)
    event = invite.event
    co_host_ids = {str(uid) for uid in event.co_hosts.values_list("pk", flat=True)}
    is_host = _can_manage_cohost_invites(request.auth, event.created_by, co_host_ids)
    is_self = invite.user_id == request.auth.pk

    if invite.status == CoHostInviteStatus.PENDING:
        _rescind_pending(invite, is_host)
    elif invite.status == CoHostInviteStatus.ACCEPTED:
        _remove_accepted(invite, request.auth, is_host, is_self)
    else:
        raise_validation(Code.CoHostInvite.NOT_REMOVABLE, status_code=400)

    event = _reload_event_for_response(event_id)
    broadcast_cohost_change(
        event,
        exclude_user_ids={str(request.auth.pk)},
        extra_user_ids={str(invite.user_id)},
    )
    return Status(200, _event_out(event, request.auth))
