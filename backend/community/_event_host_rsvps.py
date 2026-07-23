import logging
from uuid import UUID

from config.audit import audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import transaction
from ninja import Router
from ninja.responses import Status
from users.models import User as UserModel

from community._event_helpers import (
    _event_out,
    broadcast_capacity_change,
    load_event_with_stats_prefetch,
    promote_from_waitlist,
)
from community._event_rsvps import (
    _resolve_cancelled_at,
    _resolve_rsvp_status,
    _validate_rsvp_status,
)
from community._event_schemas import EventOut, HostRSVPIn
from community._events import _can_edit_event
from community._public_rsvp_shared import _email_promoted_non_members
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event, EventRSVP, RSVPStatus

router = Router()


def _apply_host_rsvp_in_transaction(
    event_id, target_user, status: str, has_plus_one: bool
) -> tuple[str, list[str]]:
    """Execute a host-driven RSVP upsert for another user inside a locked transaction.

    Unlike _apply_rsvp_in_transaction, access is already gated on the acting
    host (_can_edit_event) by the caller — this only enforces that the event
    still accepts RSVPs, not the target user's own read-visibility.

    Returns (final_status, promoted_user_ids). Raises ValidationException on failure.
    """
    event = (
        Event.objects.select_for_update()
        .prefetch_related("co_hosts", "invited_users")
        .get(id=event_id)
    )

    if not event.rsvp_enabled:
        raise_validation(Code.Event.RSVPS_NOT_ENABLED, status_code=400)
    if event.is_cancelled:
        raise_validation(Code.Event.RSVPS_CLOSED_CANCELLED, status_code=400)

    final_status, final_plus_one = _resolve_rsvp_status(event, target_user, status, has_plus_one)

    existing = EventRSVP.objects.filter(event=event, user=target_user).first()
    was_attending = existing is not None and existing.status == RSVPStatus.ATTENDING
    had_plus_one = existing is not None and existing.has_plus_one

    if (
        existing is not None
        and existing.status == final_status
        and existing.has_plus_one == final_plus_one
    ):
        return final_status, []

    EventRSVP.objects.update_or_create(
        event=event,
        user=target_user,
        defaults={
            "status": final_status,
            "has_plus_one": final_plus_one,
            "cancelled_at": _resolve_cancelled_at(existing, final_status),
        },
    )

    spot_freed = (was_attending and final_status != RSVPStatus.ATTENDING) or (
        was_attending and had_plus_one and not final_plus_one
    )
    promoted_user_ids = promote_from_waitlist(event) if spot_freed else []

    return final_status, promoted_user_ids


@router.post(
    "/events/{event_id}/rsvps/{user_id}/rsvp/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def set_guest_rsvp(request, event_id: UUID, user_id: UUID, payload: HostRSVPIn):
    """Let an event host/co-host/manager change another user's rsvp on their behalf (Issue 872)."""
    event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .filter(id=event_id)
        .first()
    )
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="set_guest_rsvp")

    _validate_rsvp_status(payload.status)

    try:
        target_user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        raise_validation(Code.User.NOT_FOUND, status_code=404)

    with transaction.atomic():
        final_status, promoted_user_ids = _apply_host_rsvp_in_transaction(
            event_id, target_user, payload.status, payload.has_plus_one
        )

    audit_log(
        logging.INFO,
        "guest_rsvp_changed",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"user_id": str(user_id), "status": final_status},
    )
    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    broadcast_capacity_change(event_id, exclude_user_ids={str(request.auth.pk)})
    _email_promoted_non_members(request, event, promoted_user_ids)
    return Status(200, _event_out(event, request.auth))


@router.delete(
    "/events/{event_id}/rsvps/{user_id}/rsvp/",
    response={204: None, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def remove_guest_rsvp(request, event_id: UUID, user_id: UUID):
    """Let an event host/co-host/manager remove another user's rsvp entirely."""
    event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users")
        .filter(id=event_id)
        .first()
    )
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="remove_guest_rsvp")

    try:
        target_user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        raise_validation(Code.User.NOT_FOUND, status_code=404)

    with transaction.atomic():
        promoted_user_ids = _remove_guest_rsvp_in_transaction(event_id, target_user)

    audit_log(
        logging.INFO,
        "guest_rsvp_removed",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"user_id": str(user_id)},
    )
    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    broadcast_capacity_change(event_id, exclude_user_ids={str(request.auth.pk)})
    _email_promoted_non_members(request, event, promoted_user_ids)
    return Status(204, None)


def _remove_guest_rsvp_in_transaction(event_id, target_user) -> list[str]:
    """Delete target_user's RSVP inside a locked transaction. No-op if none exists.

    Returns promoted_user_ids (empty unless a spot freed).
    """
    event = Event.objects.select_for_update().get(id=event_id)
    rsvp = EventRSVP.objects.filter(event=event, user=target_user).first()
    if rsvp is None:
        return []

    was_attending = rsvp.status == RSVPStatus.ATTENDING
    rsvp.delete()
    if not was_attending:
        return []

    return promote_from_waitlist(event)
