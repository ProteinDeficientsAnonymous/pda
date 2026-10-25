from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from community._cashapp_import_price import PriceSpec
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


class GapReason(StrEnum):
    SAID_PAID = "said_paid"
    ATTENDING_PAID_EVENT = "attending_paid_event"
    UNSURE_MATCH_PENDING = "unsure_match_pending"


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
class GapGuest:
    """param(pending_payment_ids): unsure proposals that may cover this guest."""

    user_id: str
    name: str
    status: RSVPStatus
    said_paid: bool
    reason: GapReason
    pending_payment_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UnreadableRow:
    payment_id: str
    row_index: int
    sender_name: str
    raw_amount: str
    raw_date: str


@dataclass(frozen=True)
class AmountMismatchLead:
    """A completed in-window payment whose amount doesn't fit the price, from a guest."""

    payment_id: str
    row_index: int
    sender_name: str
    amount: Decimal
    paid_at: datetime
    user_ids: list[str]


@dataclass(frozen=True)
class CashAppReview:
    """param(filtered): dropped row counts by FilterReason value."""

    price: PriceSpec
    total_rows: int
    proposals: list[PaymentProposal]
    gap_guests: list[GapGuest]
    unplaced_payment_ids: list[str]
    filtered: dict[str, int]
    unreadable_rows: list[UnreadableRow] = field(default_factory=list)
    amount_mismatch_leads: list[AmountMismatchLead] = field(default_factory=list)
