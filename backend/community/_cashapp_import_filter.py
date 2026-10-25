from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal

from community._cashapp_import_csv import CashAppRow
from community._cashapp_import_names import normalize_name
from community._cashapp_import_price import PeopleRange, PriceKind, PriceSpec, people_for_amount
from community._cashapp_import_types import EventPaymentContext, FilterReason

COMPLETED_STATUSES = frozenset({"COMPLETE", "COMPLETED", "PAYMENT_DEPOSITED"})
_VOID_STATUSES = frozenset({"CANCELED", "CANCELLED", "FAILED", "DECLINED"})
NON_PEER_TYPES = frozenset(
    {
        "cash in",
        "cash out",
        "direct deposit",
        "paper money",
        "paper money deposit",
        "check deposit",
        "refund",
        "bitcoin sale",
        "bitcoin buy",
        "stock sale",
        "stock buy",
        "boost",
        "interest",
        "interest payment",
    }
)


@dataclass(frozen=True)
class KeptPayment:
    """param(people): None only when the event price is unparseable."""

    row: CashAppRow
    amount: Decimal
    paid_at: datetime
    people: PeopleRange | None
    refunded: bool = False


@dataclass
class FilterResult:
    """param(amount_mismatches): rows that passed every check but the price fit."""

    kept: list[KeptPayment] = field(default_factory=list)
    dropped: Counter[FilterReason] = field(default_factory=Counter)
    unreadable: list[CashAppRow] = field(default_factory=list)
    amount_mismatches: list[KeptPayment] = field(default_factory=list)


_RefundKey = tuple[str, Decimal]


def _outgoing_by_counterparty(rows: list[CashAppRow]) -> dict[_RefundKey, list[datetime]]:
    sent: dict[_RefundKey, list[datetime]] = defaultdict(list)
    for row in rows:
        if row.amount is None or row.paid_at is None or row.amount >= 0:
            continue
        if row.status not in _VOID_STATUSES:
            sent[(normalize_name(row.sender_name), -row.amount)].append(row.paid_at)
    return sent


def _reject_reason(
    row: CashAppRow, amount: Decimal, paid_at: datetime, event: EventPaymentContext
) -> FilterReason | None:
    if amount <= 0:
        return FilterReason.OUTGOING
    if row.transaction_type.strip().lower() in NON_PEER_TYPES:
        return FilterReason.NOT_PEER_PAYMENT
    if row.status not in COMPLETED_STATUSES:
        return FilterReason.NOT_COMPLETED
    if paid_at < event.created_at:
        return FilterReason.BEFORE_EVENT_CREATED
    if event.ends_at is not None and paid_at > event.ends_at:
        return FilterReason.AFTER_EVENT_ENDED
    return None


def _evaluate(
    row: CashAppRow, event: EventPaymentContext, price: PriceSpec, seen_ids: set[str]
) -> KeptPayment | FilterReason:
    amount, paid_at = row.amount, row.paid_at
    if amount is None or paid_at is None:
        return FilterReason.UNREADABLE
    reason = _reject_reason(row, amount, paid_at, event)
    if reason is not None:
        return reason
    if row.payment_id in seen_ids:
        return FilterReason.DUPLICATE
    if price.kind == PriceKind.UNPARSEABLE:
        return KeptPayment(row, amount, paid_at, None)
    return KeptPayment(row, amount, paid_at, people_for_amount(price, amount))


def _was_refunded(payment: KeptPayment, sent: dict[_RefundKey, list[datetime]]) -> bool:
    times = sent.get((normalize_name(payment.row.sender_name), payment.amount), [])
    return any(t >= payment.paid_at for t in times)


def filter_payments(
    rows: list[CashAppRow], event: EventPaymentContext, price: PriceSpec
) -> FilterResult:
    """Window bounds are inclusive. Unparseable prices keep every amount for review."""
    result = FilterResult()
    seen_ids: set[str] = set()
    sent = _outgoing_by_counterparty(rows)
    for row in rows:
        outcome = _evaluate(row, event, price, seen_ids)
        if isinstance(outcome, FilterReason):
            result.dropped[outcome] += 1
            if outcome == FilterReason.UNREADABLE:
                result.unreadable.append(row)
            continue
        if price.kind != PriceKind.UNPARSEABLE and outcome.people is None:
            result.dropped[FilterReason.AMOUNT_MISMATCH] += 1
            result.amount_mismatches.append(outcome)
            continue
        seen_ids.add(row.payment_id)
        result.kept.append(replace(outcome, refunded=_was_refunded(outcome, sent)))
    return result
