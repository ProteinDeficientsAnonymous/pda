import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import transaction
from ninja import Router
from ninja.responses import Status
from users.models import User as UserModel
from users.permissions import PermissionKey

from community._event_helpers import (
    _can_edit_event,
    _event_out,
    broadcast_capacity_change,
    load_event_with_stats_prefetch,
)
from community._event_read_visibility import _enforce_event_read_visibility
from community._event_rsvps import (
    _resolve_cancelled_at,
    _resolve_pre_cancel_status,
    _resolve_rsvp_status,
    _validate_rsvp_status,
    payment_audit_details,
)
from community._event_schemas import (
    BulkPaymentVerifyIn,
    BulkPaymentVerifyOut,
    EventOut,
    HostRSVPIn,
    HostRSVPPaymentIn,
)
from community._payment_verification import (
    PaymentVerificationChange,
    apply_payment_verification,
    record_payment_verification,
)
from community._rsvp_status_emails import email_host_set_rsvp_status, email_promoted_users
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community._waitlist import promote_from_waitlist
from community.models import MATCHABLE_RSVP_STATUSES, Event, EventRSVP, RSVPStatus

router = Router()


def _resolve_host_rsvp_status(
    event: Event, target_user, status: str, has_plus_one: bool, existing: EventRSVP | None
) -> tuple[str, bool]:
    if event.is_past:
        # Capacity is moot once the event is over — never waitlist an after-the-fact add.
        return status, has_plus_one and event.allow_plus_ones
    return _resolve_rsvp_status(event, target_user, status, has_plus_one, existing)


def _needs_host_verification(existing: EventRSVP | None, paid_confirmed: bool) -> bool:
    # False means "not asserting payment", so it never clears an existing verification.
    return paid_confirmed and (existing is None or existing.payment_verified_at is None)


def _host_rsvp_unchanged(
    existing: EventRSVP | None, final_status: str, final_plus_one: bool
) -> bool:
    return (
        existing is not None
        and existing.status == final_status
        and existing.has_plus_one == final_plus_one
    )


def _host_spot_freed(existing: EventRSVP | None, final_status: str, final_plus_one: bool) -> bool:
    if existing is None or existing.status != RSVPStatus.ATTENDING:
        return False
    return final_status != RSVPStatus.ATTENDING or (existing.has_plus_one and not final_plus_one)


def _apply_host_rsvp_in_transaction(
    event_id, target_user, payload: HostRSVPIn, actor
) -> tuple[str, list[str], str | None]:
    """Host-driven RSVP upsert; never payment-gated, and paid_confirmed marks the payment host-verified."""
    event = Event.objects.select_for_update().get(id=event_id)

    if not event.rsvp_enabled:
        raise_validation(Code.Event.RSVPS_NOT_ENABLED, status_code=400)
    if event.is_cancelled:
        raise_validation(Code.Event.RSVPS_CLOSED_CANCELLED, status_code=400)

    existing = EventRSVP.objects.filter(event=event, user=target_user).first()
    final_status, final_plus_one = _resolve_host_rsvp_status(
        event, target_user, payload.status, payload.has_plus_one, existing
    )
    previous_status = getattr(existing, "status", None)
    # Never stamp here: verification stamps paid_confirmed_at == payment_verified_at itself.
    new_confirmed_at = existing.paid_confirmed_at if existing is not None else None
    needs_verification = _needs_host_verification(existing, payload.paid_confirmed)

    if not needs_verification and _host_rsvp_unchanged(existing, final_status, final_plus_one):
        return final_status, [], previous_status

    rsvp, _ = EventRSVP.objects.update_or_create(
        event=event,
        user=target_user,
        defaults={
            "status": final_status,
            "has_plus_one": final_plus_one,
            "cancelled_at": _resolve_cancelled_at(existing, final_status),
            "pre_cancel_status": _resolve_pre_cancel_status(existing, final_status),
            "paid_confirmed_at": new_confirmed_at,
        },
    )
    if needs_verification:
        apply_payment_verification(rsvp, verified=True, actor=actor)

    spot_freed = _host_spot_freed(existing, final_status, final_plus_one)
    promoted_user_ids = promote_from_waitlist(event) if spot_freed else []

    return final_status, promoted_user_ids, previous_status


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
        final_status, promoted_user_ids, previous_status = _apply_host_rsvp_in_transaction(
            event_id, target_user, payload, request.auth
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
    if not event.is_past:
        email_host_set_rsvp_status(request, event, target_user, previous_status, final_status)
    email_promoted_users(request, event, promoted_user_ids)
    return Status(200, _event_out(event, request.auth))


def _apply_payment_change_in_transaction(
    event_id, user_id, verified: bool, actor
) -> PaymentVerificationChange:
    """Lock one rsvp and set or clear its host-verified mark; the guest's own attestation stays."""
    rsvp = EventRSVP.objects.select_for_update().filter(event_id=event_id, user_id=user_id).first()
    if rsvp is None:
        raise_validation(Code.Event.RSVP_NOT_FOUND, status_code=404)
    return apply_payment_verification(rsvp, verified=verified, actor=actor)


@router.patch(
    "/events/{event_id}/rsvps/{user_id}/payment/",
    response={200: EventOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def set_guest_payment(request, event_id: UUID, user_id: UUID, payload: HostRSVPPaymentIn):
    """Let a host verify or un-verify a guest's payment without touching their rsvp status."""
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
        change = _apply_payment_change_in_transaction(
            event_id, user_id, payload.paid_confirmed, request.auth
        )

    record_payment_verification(request, event, change)
    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    return Status(200, _event_out(event, request.auth))


CASHAPP_IMPORT_SOURCE = "cashapp_import"


def _verify_payments_in_transaction(
    event_id, user_ids: list[UUID], actor
) -> tuple[list[tuple[EventRSVP, PaymentVerificationChange]], list[str]]:
    """All-or-nothing: every id needs a matchable rsvp; already-verified guests are skipped."""
    rsvps = {
        str(rsvp.user_id): rsvp
        for rsvp in EventRSVP.objects.select_for_update()
        .filter(event_id=event_id, user_id__in=user_ids, status__in=MATCHABLE_RSVP_STATUSES)
        .order_by("user_id")
    }
    missing = [str(uid) for uid in user_ids if str(uid) not in rsvps]
    if missing:
        raise_validation(
            Code.Event.PAYMENT_VERIFY_NOT_GUESTS, status_code=400, user_ids=", ".join(missing)
        )
    applied: list[tuple[EventRSVP, PaymentVerificationChange]] = []
    skipped: list[str] = []
    for uid in user_ids:
        rsvp = rsvps[str(uid)]
        if rsvp.payment_verified_at is not None:
            skipped.append(str(uid))
        else:
            applied.append((rsvp, apply_payment_verification(rsvp, verified=True, actor=actor)))
    return applied, skipped


def _load_payment_import_event(request, event_id: UUID) -> Event:
    """Same rules as the guest list: the event is readable and the caller may see payments."""
    event = Event.objects.select_related("created_by").filter(id=event_id).first()
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    _enforce_event_read_visibility(event, request.auth)
    if not _can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="verify_guest_payments")
    return event


@router.post(
    "/events/{event_id}/rsvps/payments/verify/",
    response={
        200: BulkPaymentVerifyOut,
        400: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        429: ErrorOut,
    },
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def verify_guest_payments(request, event_id: UUID, payload: BulkPaymentVerifyIn):
    """Bulk-verify attending/waitlisted guests' payments; needs import_payments and hosting rights."""
    if not request.auth.has_permission(PermissionKey.IMPORT_PAYMENTS):
        raise_validation(Code.Perm.DENIED, status_code=403, action="verify_guest_payments")
    event = _load_payment_import_event(request, event_id)

    user_ids = list(dict.fromkeys(payload.user_ids))
    with transaction.atomic():
        applied, skipped = _verify_payments_in_transaction(event_id, user_ids, request.auth)

    for rsvp, change in applied:
        record_payment_verification(request, event, change, source=CASHAPP_IMPORT_SOURCE, rsvp=rsvp)
    total = EventRSVP.objects.filter(event_id=event_id, payment_verified_at__isnull=False).count()
    return Status(
        200,
        BulkPaymentVerifyOut(
            verified_user_ids=[change.user_id for _, change in applied],
            already_verified_user_ids=skipped,
            event_verified_total=total,
        ),
    )


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
    email_promoted_users(request, event, promoted_user_ids)
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
