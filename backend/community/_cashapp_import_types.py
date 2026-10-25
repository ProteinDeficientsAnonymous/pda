from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class FilterReason(StrEnum):
    UNREADABLE = "unreadable"
    DUPLICATE = "duplicate"
    OUTGOING = "outgoing"
    NOT_PEER_PAYMENT = "not_peer_payment"
    NOT_COMPLETED = "not_completed"
    BEFORE_EVENT_CREATED = "before_event_created"
    AFTER_EVENT_ENDED = "after_event_ended"
    AMOUNT_MISMATCH = "amount_mismatch"


@dataclass(frozen=True)
class EventPaymentContext:
    """param(ends_at): end, else start plus a grace period; None when the event has neither."""

    created_at: datetime
    ends_at: datetime | None
    price: str
    is_paid_event: bool
