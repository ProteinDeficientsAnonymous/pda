import logging
from decimal import Decimal
from uuid import UUID

import httpx
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel

from community.models import Event, EventRSVP, EventStatus, RSVPStatus
from community.paypal._client import create_order, paypal_configured
from community.paypal.price import offered_paypal_price
from community.shared import ErrorOut
from community.validation import Code, raise_validation

logger = logging.getLogger("pda")

router = Router()

PAYABLE_RSVP_STATUSES = (RSVPStatus.ATTENDING, RSVPStatus.WAITLISTED, RSVPStatus.MAYBE)


class PayPalOrderOut(BaseModel):
    order_id: str
    amount: Decimal


def unpaid_rsvp(event: Event, user) -> EventRSVP | None:
    return EventRSVP.objects.filter(
        event=event,
        user=user,
        status__in=PAYABLE_RSVP_STATUSES,
        payment_verified_at__isnull=True,
    ).first()


@router.post(
    "/events/{event_id}/paypal/order/",
    response={200: PayPalOrderOut, frozenset({400, 404, 429, 502, 503}): ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/h")
def create_paypal_order(request, event_id: UUID):
    if not paypal_configured():
        return Status(503, {"detail": "paypal is not configured"})
    event = Event.objects.filter(id=event_id).first()
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    amount = offered_paypal_price(event)
    if amount is None or event.status != EventStatus.ACTIVE:
        raise_validation(Code.Event.PAYPAL_NOT_ACCEPTED, status_code=400)
    rsvp = unpaid_rsvp(event, request.auth)
    if rsvp is None:
        raise_validation(Code.Event.PAYPAL_NOTHING_TO_PAY, status_code=400)
    try:
        order_id = create_order(rsvp_id=str(rsvp.pk), amount=amount, description=event.title)
    except httpx.HTTPError:
        logger.exception("paypal_create_order_failed", extra={"event_id": str(event_id)})
        return Status(502, {"detail": "paypal is unavailable, try again"})
    return Status(200, PayPalOrderOut(order_id=order_id, amount=amount))
