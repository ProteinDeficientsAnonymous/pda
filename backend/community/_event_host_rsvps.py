import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import transaction
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from notifications.service import create_payment_revoked_notification
from users.models import User as UserModel

from community._event_helpers import (
    _event_out,
    broadcast_capacity_change,
    load_event_with_stats_prefetch,
    promote_from_waitlist,
)
from community._event_rsvps import (
    _resolve_cancelled_at,
    _resolve_paid_confirmed_at,
    _resolve_previous_status,
    _resolve_rsvp_status,
    _validate_rsvp_status,
    payment_audit_details,
)
from community._event_schemas import EventOut, HostRSVPIn, HostRSVPPaymentIn
from community._events import _can_edit_event
from community._public_rsvp_shared import _email_promoted_non_members
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event, EventRSVP, RSVPStatus

router = Router()


def _apply_host_rsvp_in_transaction(
    event_id, target_user, status: str, has_plus_one: bool, paid_confirmed: bool = False
) -> tuple[str, list[str]]:
    """Host-driven RSVP upsert; unlike _apply_rsvp_in_transaction, never subject to the payment gate."""
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
    new_confirmed_at = _resolve_paid_confirmed_at(existing, paid_confirmed, final_status)

    if (
        existing is not None
        and existing.status == final_status
        and existing.has_plus_one == final_plus_one
        and existing.paid_confirmed_at == new_confirmed_at
    ):
        return final_status, []

    EventRSVP.objects.update_or_create(
        event=event,
        user=target_user,
        defaults={
            "status": final_status,
            "has_plus_one": final_plus_one,
            "cancelled_at": _resolve_cancelled_at(existing, final_status),
            "previous_status": _resolve_previous_status(existing, final_status),
            "paid_confirmed_at": new_confirmed_at,
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
            event_id, target_user, payload.status, payload.has_plus_one, payload.paid_confirmed
        )

    audit_log(
        logging.INFO,
        "guest_rsvp_changed",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT,
            id=str(event_id),
            details={
                "user_id": str(user_id),
                "status": final_status,
                **payment_audit_details(event_id, user_id),
            },
        ),
    )
    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    broadcast_capacity_change(event_id, exclude_user_ids={str(request.auth.pk)})
    _email_promoted_non_members(request, event, promoted_user_ids)
    return Status(200, _event_out(event, request.auth))


def _apply_payment_change_in_transaction(event_id, user_id, paid_confirmed: bool) -> bool:
    """Set or clear the payment stamp on a locked rsvp row. Returns whether it was paid before.

    Clearing re-gates the guest on their next attending write. The record that
    they once paid, and who retracted it, lives in the audit log.
    """
    rsvp = EventRSVP.objects.select_for_update().filter(event_id=event_id, user_id=user_id).first()
    if rsvp is None:
        raise_validation(Code.Event.RSVP_NOT_FOUND, status_code=404)
    was_paid = rsvp.paid_confirmed_at is not None
    if paid_confirmed:
        rsvp.paid_confirmed_at = rsvp.paid_confirmed_at or timezone.now()
    else:
        rsvp.paid_confirmed_at = None
    rsvp.save(update_fields=["paid_confirmed_at", "updated_at"])
    return was_paid


@router.patch(
    "/events/{event_id}/rsvps/{user_id}/payment/",
    response={200: EventOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def set_guest_payment(request, event_id: UUID, user_id: UUID, payload: HostRSVPPaymentIn):
    """Let a host confirm or retract a guest's payment without touching their rsvp status."""
    event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .filter(id=event_id)
        .first()
    )
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="set_guest_payment")

    with transaction.atomic():
        was_paid = _apply_payment_change_in_transaction(event_id, user_id, payload.paid_confirmed)

    is_revoke = was_paid and not payload.paid_confirmed
    audit_log(
        logging.INFO,
        "guest_payment_revoked" if is_revoke else "guest_payment_changed",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT,
            id=str(event_id),
            details={
                "user_id": str(user_id),
                "was_paid": was_paid,
                **payment_audit_details(event_id, user_id),
            },
        ),
    )
    if is_revoke:
        create_payment_revoked_notification(event, str(user_id))
    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
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
        target=AuditTarget(
            type=AuditTargetType.EVENT, id=str(event_id), details={"user_id": str(user_id)}
        ),
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
