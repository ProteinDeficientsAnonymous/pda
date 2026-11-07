from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from community.validation import Code, raise_validation

_CENT = Decimal("0.01")
MAX_PRICE = Decimal("100000")


def parse_price(v: object) -> Decimal | None:
    """Blank means no price. Accepts "10", "$10.50", or a number."""
    if v is None or isinstance(v, bool):
        return None
    text = str(v).strip().removeprefix("$").strip().replace(",", "")
    if not text:
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise_validation(Code.Event.PRICE_INVALID, field="price")
    if not amount.is_finite() or amount <= 0 or amount >= MAX_PRICE:
        raise_validation(Code.Event.PRICE_INVALID, field="price")
    return amount.quantize(_CENT, rounding=ROUND_HALF_UP)


def price_text(amount: Decimal | str | None) -> str:
    """Wire format: "" for no price, whole dollars without cents ("10"), else "33.50"."""
    if amount is None or amount == "":
        return ""
    amount = Decimal(amount)
    if amount == amount.to_integral_value():
        return str(amount.quantize(Decimal(1)))
    return str(amount.quantize(_CENT))
