import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from community.models import Event, EventRSVP
from community.paypal.price import paypal_price
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


def covers_price(amount: dict, event: Event) -> bool:
    if amount.get("currency_code") != "USD" or not event.price:
        return False
    try:
        return Decimal(amount.get("value", "")) >= paypal_price(Decimal(event.price))
    except (InvalidOperation, TypeError):
        return False


def record_capture(request, capture: dict) -> EventRSVP | None:
    """Mark the rsvp in the capture's custom_id paid; a capture already recorded is a no-op.

    return(None): the capture isn't completed, names no rsvp, or doesn't cover the price.
    """
    if capture.get("status") != CAPTURE_COMPLETED:
        return None
    with transaction.atomic():
        rsvp = _locked_rsvp(capture.get("custom_id"))
        if rsvp is None:
            logger.warning("paypal_capture_without_rsvp", extra={"capture_id": capture.get("id")})
            return None
        if rsvp.paypal_capture_id is not None:
            if rsvp.paypal_capture_id != capture.get("id"):
                logger.warning(
                    "paypal_duplicate_capture",
                    extra={"capture_id": capture.get("id"), "recorded": rsvp.paypal_capture_id},
                )
            return rsvp
        # Buyers can create orders client-side with any custom_id, so the amount is checked here.
        if not covers_price(capture.get("amount") or {}, rsvp.event):
            logger.warning("paypal_capture_short", extra={"capture_id": capture.get("id")})
            return None
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
        rsvp.save(
            update_fields=[
                "paid_confirmed_at",
                "payment_verified_at",
                "paypal_capture_id",
                "updated_at",
            ]
        )
        record_payment_verification(request, rsvp.event, change, source="paypal", rsvp=rsvp)
    return rsvp
