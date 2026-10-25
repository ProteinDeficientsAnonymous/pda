from collections import defaultdict
from collections.abc import Collection
from datetime import datetime, timedelta

from community._cashapp_import_csv import CashAppRow, parse_cashapp_csv
from community._cashapp_import_filter import filter_payments
from community._cashapp_import_matching import (
    amount_mismatch_leads,
    match_payments,
)
from community._cashapp_import_price import PriceKind, parse_event_price
from community._cashapp_import_types import (
    CashAppReview,
    EventPaymentContext,
    GapGuest,
    GapReason,
    GuestRecord,
    MatchConfidence,
    PaymentProposal,
    UnreadableRow,
)
from community._rsvp_payment import event_requires_payment_confirmation
from community.models import MATCHABLE_RSVP_STATUSES, Event, RSVPStatus

NO_END_GRACE = timedelta(hours=6)


def _gap_reason(guest: GuestRecord, event: EventPaymentContext) -> GapReason | None:
    if guest.said_paid:
        return GapReason.SAID_PAID
    if event.is_paid_event and guest.status == RSVPStatus.ATTENDING:
        return GapReason.ATTENDING_PAID_EVENT
    return None


def _pending_by_guest(proposals: list[PaymentProposal]) -> dict[str, list[str]]:
    pending: dict[str, list[str]] = defaultdict(list)
    for p in proposals:
        if p.confidence == MatchConfidence.UNSURE:
            for uid in dict.fromkeys(p.user_ids + p.candidate_user_ids):
                pending[uid].append(p.payment_id)
    return pending


def build_gap_list(
    guests: list[GuestRecord],
    proposals: list[PaymentProposal],
    event: EventPaymentContext,
    verified_user_ids: Collection[str],
) -> list[GapGuest]:
    """Only a confident proposal takes a guest off the list; unsure ones are flagged pending."""
    covered = {
        uid for p in proposals if p.confidence == MatchConfidence.CONFIDENT for uid in p.user_ids
    }
    pending = _pending_by_guest(proposals)
    gaps = []
    for guest in guests:
        if guest.user_id in covered or guest.user_id in verified_user_ids:
            continue
        reason = _gap_reason(guest, event) if guest.status in MATCHABLE_RSVP_STATUSES else None
        if reason is None:
            continue
        pending_ids = pending.get(guest.user_id, [])
        gaps.append(
            GapGuest(
                user_id=guest.user_id,
                name=guest.display_name,
                status=guest.status,
                said_paid=guest.said_paid,
                reason=GapReason.UNSURE_MATCH_PENDING if pending_ids else reason,
                pending_payment_ids=pending_ids,
            )
        )
    return sorted(gaps, key=lambda g: (not g.said_paid, g.name.lower()))


def _unreadable(rows: list[CashAppRow]) -> list[UnreadableRow]:
    return [
        UnreadableRow(r.payment_id, r.row_index, r.sender_name, r.raw_amount, r.raw_date)
        for r in rows
    ]


def review_rows(
    rows: list[CashAppRow],
    event: EventPaymentContext,
    guests: list[GuestRecord],
    verified_user_ids: Collection[str] = (),
) -> CashAppReview:
    price = parse_event_price(event.price)
    filtered = filter_payments(rows, event, price)
    proposals = match_payments(filtered.kept, guests)
    return CashAppReview(
        price=price,
        total_rows=len(rows),
        proposals=proposals,
        gap_guests=build_gap_list(guests, proposals, event, verified_user_ids),
        unplaced_payment_ids=[
            p.payment_id for p in proposals if p.confidence == MatchConfidence.UNMATCHED
        ],
        filtered={reason.value: count for reason, count in filtered.dropped.items()},
        unreadable_rows=_unreadable(filtered.unreadable),
        amount_mismatch_leads=amount_mismatch_leads(filtered.amount_mismatches, guests),
    )


def review_cashapp_csv(
    csv_text: str,
    event: EventPaymentContext,
    guests: list[GuestRecord],
    verified_user_ids: Collection[str] = (),
) -> CashAppReview:
    return review_rows(parse_cashapp_csv(csv_text), event, guests, verified_user_ids)


def _ends_at(event: Event) -> datetime | None:
    if event.end_datetime is not None:
        return event.end_datetime
    if event.start_datetime is not None:
        return event.start_datetime + NO_END_GRACE
    return None


def load_payment_context(event: Event) -> EventPaymentContext:
    """Paid when the app gates on payment or the price reads as a dollar amount."""
    is_paid = event_requires_payment_confirmation(event) or (
        parse_event_price(event.price).kind != PriceKind.UNPARSEABLE
    )
    return EventPaymentContext(
        created_at=event.created_at,
        ends_at=_ends_at(event),
        price=event.price,
        is_paid_event=is_paid,
    )


def load_guest_records(event: Event) -> list[GuestRecord]:
    rsvps = event.rsvps.filter(status__in=MATCHABLE_RSVP_STATUSES).select_related("user")
    return [
        GuestRecord(
            user_id=str(rsvp.user_id),
            first_name=rsvp.user.first_name,
            last_name=rsvp.user.last_name,
            nickname=rsvp.user.nickname,
            status=RSVPStatus(rsvp.status),
            has_plus_one=rsvp.has_plus_one,
            said_paid=rsvp.paid_confirmed_at is not None,
        )
        for rsvp in rsvps
    ]
