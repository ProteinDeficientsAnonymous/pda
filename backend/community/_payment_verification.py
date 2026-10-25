import logging
from dataclasses import dataclass

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.utils import timezone
from notifications.service import create_payment_revoked_notification

from community._event_rsvps import payment_audit_details
from community.models import Event, EventRSVP


@dataclass(frozen=True, slots=True)
class PaymentVerificationChange:
    user_id: str
    was_paid: bool
    was_verified: bool
    verified: bool
    # The guest never claimed payment; the host's verification stamped it for them.
    host_stamped: bool = False

    @property
    def revoked(self) -> bool:
        return self.was_verified and not self.verified

    @property
    def notifies_guest(self) -> bool:
        return self.revoked and not self.host_stamped


def apply_payment_verification(
    rsvp: EventRSVP, *, verified: bool, actor
) -> PaymentVerificationChange:
    """Set or clear the host-verified mark on a caller-locked rsvp; clearing keeps a guest's own attestation."""
    change = PaymentVerificationChange(
        user_id=str(rsvp.user_id),
        was_paid=rsvp.paid_confirmed_at is not None,
        was_verified=rsvp.payment_verified_at is not None,
        verified=verified,
        host_stamped=(
            rsvp.payment_verified_at is not None
            and rsvp.paid_confirmed_at == rsvp.payment_verified_at
        ),
    )
    if verified:
        now = timezone.now()
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


def record_payment_verification(request, event: Event, change: PaymentVerificationChange) -> None:
    """Audit a verification change; notify the guest when a host retracts a payment they claimed."""
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
                **payment_audit_details(event.id, change.user_id),
            },
        ),
    )
    if change.notifies_guest:
        create_payment_revoked_notification(event, change.user_id)
