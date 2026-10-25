import math
import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class PriceKind(StrEnum):
    EXACT = "exact"
    RANGE = "range"
    UNPARSEABLE = "unparseable"


@dataclass(frozen=True)
class PriceSpec:
    """param(high): None on an open-ended range like "$10+"."""

    kind: PriceKind
    low: Decimal | None = None
    high: Decimal | None = None


@dataclass(frozen=True)
class PeopleRange:
    low: int
    high: int

    def includes(self, count: int) -> bool:
        return self.low <= count <= self.high


UNPARSEABLE = PriceSpec(PriceKind.UNPARSEABLE)

_NUM = r"\d{1,3}(?:,\d{3})+(?!\d)(?:\.\d+)?|\d+(?:\.\d+)?"
_NUMBER_RE = re.compile(rf"(\$\s*)?({_NUM})")
_RANGE_RE = re.compile(
    rf"(\$\s*)?({_NUM})(?:\s*[-–—/]\s*|\s+to\s+|,(?=\d)(?!\d{{3}}(?!\d)))(\$\s*)?({_NUM})"
)
_OPEN_ENDED_RE = re.compile(r"\d\s*\+|or more|and up")
_ANY_AMOUNT_PHRASES = ("pay what you", "pwyc", "donation", "free")


def _to_decimal(number: str) -> Decimal:
    return Decimal(number.replace(",", ""))


def _spec_for(numbers: list[Decimal], text: str) -> PriceSpec:
    if not numbers or len(numbers) > 2 or min(numbers) <= 0:
        return UNPARSEABLE
    if len(numbers) == 2:
        return PriceSpec(PriceKind.RANGE, min(numbers), max(numbers))
    if _OPEN_ENDED_RE.search(text):
        return PriceSpec(PriceKind.RANGE, numbers[0], None)
    return PriceSpec(PriceKind.EXACT, numbers[0], numbers[0])


def _range_in(text: str, has_dollar: bool) -> PriceSpec | None:
    for match in _RANGE_RE.finditer(text):
        dollar_a, low, dollar_b, high = match.groups()
        if has_dollar and not (dollar_a or dollar_b):
            continue
        return _spec_for([_to_decimal(low), _to_decimal(high)], text)
    return None


def parse_event_price(raw: str) -> PriceSpec:
    """Once any number has a "$", bare numbers ("2 for $25", "doors at 7") are ignored."""
    text = raw.strip().lower()
    if not text or any(phrase in text for phrase in _ANY_AMOUNT_PHRASES):
        return UNPARSEABLE
    found = _NUMBER_RE.findall(text)
    has_dollar = any(dollar for dollar, _ in found)
    numbers = [_to_decimal(n) for dollar, n in found if dollar or not has_dollar]
    if len(numbers) > 2:
        return UNPARSEABLE
    return _range_in(text, has_dollar) or _spec_for(numbers, text)


def people_for_amount(price: PriceSpec, amount: Decimal) -> PeopleRange | None:
    """Head counts n where amount / n is a valid price. return(None): no fit, or price unparseable."""
    if price.low is None or amount <= 0:
        return None
    most = math.floor(amount / price.low)
    fewest = 1 if price.high is None else math.ceil(amount / price.high)
    if price.kind == PriceKind.EXACT and amount % price.low != 0:
        return None
    if fewest > most:
        return None
    return PeopleRange(max(fewest, 1), most)
