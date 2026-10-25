import logging
from dataclasses import dataclass
from datetime import timedelta

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.utils import timezone
from notifications.service import create_payment_revoked_notification
from users.models import User

from community._event_rsvps import payment_audit_details, payment_audit_fields
from community.models import Event, EventRSVP

MISCLICK_WINDOW = timedelta(minutes=10)


@dataclass(frozen=True, slots=True)
class PaymentVerificationChange:
    user_id: str
    was_paid: bool
    was_verified: bool
    verified: bool
    # The guest never claimed payment; the host's verification stamped it for them.
    host_stamped: bool = False
    # A host-stamped verification undone soon after it was made, i.e. a mis-click.
    quick_undo: bool = False

    @property
    def revoked(self) -> bool:
        return self.was_verified and not self.verified

    @property
    def notifies_guest(self) -> bool:
        return self.revoked and not self.quick_undo


def _host_stamped(rsvp: EventRSVP) -> bool:
    return (
        rsvp.payment_verified_at is not None and rsvp.paid_confirmed_at == rsvp.payment_verified_at
    )


def apply_payment_verification(
    rsvp: EventRSVP, *, verified: bool, actor: User
) -> PaymentVerificationChange:
    """Set or clear the host-verified mark on a caller-locked rsvp; clearing keeps a guest's own attestation."""
    now = timezone.now()
    host_stamped = _host_stamped(rsvp)
    verified_at = rsvp.payment_verified_at
    change = PaymentVerificationChange(
        user_id=str(rsvp.user_id),
        was_paid=rsvp.paid_confirmed_at is not None,
        was_verified=verified_at is not None,
        verified=verified,
        host_stamped=host_stamped,
        quick_undo=(
            not verified
            and host_stamped
            and verified_at is not None
            and now - verified_at <= MISCLICK_WINDOW
        ),
    )
    if verified:
        # A host-verified guest must never be payment-gated.
        rsvp.paid_confirmed_at = rsvp.paid_confirmed_at or now
        if not change.was_verified:
            rsvp.payment_verified_at = now
            rsvp.payment_verified_by = actor
    else:
        if change.host_stamped:
            rsvp.paid_confirmed_at = None
        rsvp.payment_verified_at = None
        rsvp.payment_verified_by = None
    rsvp.save(
        update_fields=[
            "paid_confirmed_at",
            "payment_verified_at",
            "payment_verified_by",
            "updated_at",
        ]
    )
    return change


def _rsvp_audit_details(rsvp: EventRSVP) -> dict:
    return payment_audit_fields(
        rsvp.paid_confirmed_at, rsvp.payment_verified_at, rsvp.payment_verified_by_id
    )


def record_payment_verification(
    request,
    event: Event,
    change: PaymentVerificationChange,
    *,
    source: str | None = None,
    rsvp: EventRSVP | None = None,
) -> None:
    """Audit a verification change; notify the guest unless it undoes a fresh host-stamped mark.

    param(rsvp): the row as just saved, to skip re-reading it; omitted, the row is re-read.
    """
    stored = _rsvp_audit_details(rsvp) if rsvp else payment_audit_details(event.id, change.user_id)
    audit_log(
        logging.INFO,
        "guest_payment_revoked" if change.revoked else "guest_payment_changed",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT,
            id=str(event.id),
            details={
                "user_id": change.user_id,
                "was_paid": change.was_paid,
                "was_verified": change.was_verified,
                "host_stamped": change.host_stamped,
                **stored,
                **({"source": source} if source else {}),
            },
        ),
    )
    if change.notifies_guest:
        create_payment_revoked_notification(event, change.user_id)
