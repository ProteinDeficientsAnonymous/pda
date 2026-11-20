import logging

from django.db import transaction
from django.utils import timezone

from community.models import EventRSVP
from community.rsvps.payment_verification import (
    PaymentVerificationChange,
    record_payment_verification,
)

logger = logging.getLogger("pda")

CAPTURE_COMPLETED = "COMPLETED"


def _locked_rsvp(custom_id: str | None) -> EventRSVP | None:
    try:
        rsvp_id = int(custom_id or "")
    except ValueError:
        return None
    return EventRSVP.objects.select_for_update().select_related("event").filter(pk=rsvp_id).first()


def record_capture(request, capture: dict) -> EventRSVP | None:
    """Mark the rsvp in the capture's custom_id paid; a capture already recorded is a no-op.

    return(None): the capture isn't completed or names no rsvp.
    """
    if capture.get("status") != CAPTURE_COMPLETED:
        return None
    with transaction.atomic():
        rsvp = _locked_rsvp(capture.get("custom_id"))
        if rsvp is None:
            logger.warning("paypal_capture_without_rsvp", extra={"capture_id": capture.get("id")})
            return None
        if rsvp.paypal_capture_id is not None:
            return rsvp
        now = timezone.now()
        change = PaymentVerificationChange(
            user_id=str(rsvp.user_id),
            was_paid=rsvp.paid_confirmed_at is not None,
            was_verified=rsvp.payment_verified_at is not None,
            verified=True,
        )
        rsvp.paid_confirmed_at = rsvp.paid_confirmed_at or now
        rsvp.payment_verified_at = rsvp.payment_verified_at or now
        rsvp.paypal_capture_id = capture["id"]
        rsvp.save(update_fields=["paid_confirmed_at", "payment_verified_at", "paypal_capture_id"])
        record_payment_verification(request, rsvp.event, change, source="paypal", rsvp=rsvp)
    return rsvp
