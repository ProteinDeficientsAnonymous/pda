from decimal import ROUND_CEILING, Decimal

from community.models import Event

# PayPal Checkout US commercial rate (paypal.com business fees, updated 2026-11-04).
PERCENT_FEE = Decimal("0.0349")
FIXED_FEE = Decimal("0.49")
_CENT = Decimal("0.01")


def paypal_price(amount: Decimal) -> Decimal:
    """Smallest charge that nets `amount` after PayPal's fee."""
    return ((amount + FIXED_FEE) / (1 - PERCENT_FEE)).quantize(_CENT, rounding=ROUND_CEILING)


def offered_paypal_price(event: Event, people: int = 1) -> Decimal | None:
    """return(None): the event doesn't take paypal or has no price."""
    if not event.accept_paypal or not event.price:
        return None
    return paypal_price(Decimal(event.price) * people)
