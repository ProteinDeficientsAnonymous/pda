from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from community.models import RSVPStatus


class MatchConfidence(StrEnum):
    CONFIDENT = "confident"
    UNSURE = "unsure"
    UNMATCHED = "unmatched"


class MatchSource(StrEnum):
    SENDER = "sender"
    NOTE = "note"
    SENDER_AND_NOTE = "sender_and_note"
    NONE = "none"


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


@dataclass(frozen=True)
class GuestRecord:
    user_id: str
    first_name: str
    last_name: str
    nickname: str
    status: RSVPStatus
    has_plus_one: bool = False
    said_paid: bool = False

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.nickname

    @property
    def headcount(self) -> int:
        return 2 if self.has_plus_one else 1


@dataclass(frozen=True)
class PaymentProposal:
    """param(user_ids): guests this payment would verify. param(candidate_user_ids): ambiguous alternatives."""

    payment_id: str
    row_index: int
    sender_name: str
    note: str
    amount: Decimal
    paid_at: datetime
    confidence: MatchConfidence
    reason: str
    matched_by: MatchSource
    user_ids: list[str] = field(default_factory=list)
    candidate_user_ids: list[str] = field(default_factory=list)
    people_low: int | None = None
    people_high: int | None = None


@dataclass(frozen=True)
class AmountMismatchLead:
    """A completed in-window payment whose amount doesn't fit the price, from a guest."""

    payment_id: str
    row_index: int
    sender_name: str
    amount: Decimal
    paid_at: datetime
    user_ids: list[str]
