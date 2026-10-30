import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from asgiref.sync import sync_to_async
from community._cashapp_import_price import PriceSpec
from community._cashapp_import_review import (
    load_guests_and_verified,
    load_payment_context,
    review_cashapp_csv,
)
from community._cashapp_import_types import (
    AmountMismatchLead,
    CashAppReview,
    GapGuest,
    GuestRecord,
    MatchConfidence,
    PaymentProposal,
    UnreadableRow,
)
from community._event_helpers import _can_edit_event
from community._event_read_visibility import _enforce_event_read_visibility
from community._tentative_member_access import event_viewer_for
from community._validation import Code, ValidationException, raise_validation
from community.models import Event, parse_event_ref
from django.conf import settings
from django.core.cache import caches
from mcp.server.mcpserver.exceptions import ToolError
from users.models import User

from mcp_gateway.server import BASE_URL
from mcp_gateway.view_calls import validation_tool_error

REVIEW_TTL_SECONDS = 60 * 60


def csv_digest(csv_text: str) -> str:
    return hashlib.sha256(csv_text.encode()).hexdigest()


def review_cache_key(user_pk: Any, event_id: str, review_id: str) -> str:
    return f"mcp-cashapp-review:{user_pk}:{event_id}:{review_id}"


@dataclass(frozen=True)
class LoadedReview:
    event: dict[str, Any]
    review: CashAppReview
    guests: dict[str, GuestRecord]
    verified: frozenset[str]
    review_id: str
    csv_text: str = field(repr=False)
    record: Event = field(repr=False, compare=False)

    @property
    def event_id(self) -> str:
        return self.event["id"]

    def person(self, user_id: str) -> dict[str, Any]:
        guest = self.guests.get(user_id)
        return {
            "user_id": user_id,
            "name": guest.display_name if guest else None,
            "status": guest.status.value if guest else None,
            "already_verified": user_id in self.verified,
        }


def _visible_event(user: User, event_ref: str) -> Event:
    """The website's event read rules, without serializing the event."""
    event = (
        Event.objects.prefetch_related("co_hosts").filter(parse_event_ref(event_ref).as_q()).first()
    )
    try:
        if event is None:
            raise_validation(Code.Event.NOT_FOUND, status_code=404)
        _enforce_event_read_visibility(event, event_viewer_for(user, event))
    except ValidationException as exc:
        raise validation_tool_error(exc) from exc
    return event


def _review_event(
    user: User, event: Event, csv_text: str
) -> tuple[CashAppReview, list[GuestRecord], set[str]]:
    """Payment status follows the guest list's rule: co-hosts and manage_events only."""
    try:
        if not _can_edit_event(user, event):
            raise_validation(Code.Perm.DENIED, status_code=403, action="review_cashapp_payments")
        guests, verified = load_guests_and_verified(event)
        review = review_cashapp_csv(csv_text, load_payment_context(event), guests, verified)
    except ValidationException as exc:
        raise validation_tool_error(exc) from exc
    return review, guests, verified


async def _review(user: User, event: Event, csv_text: str) -> LoadedReview:
    review, guests, verified = await sync_to_async(_review_event)(user, event, csv_text)
    summary = {
        "id": str(event.id),
        "title": event.title,
        "price": event.price,
        "url": f"{BASE_URL}/events/{event.slug or event.id}",
    }
    guest_map = {g.user_id: g for g in guests}
    return LoadedReview(
        summary, review, guest_map, frozenset(verified), csv_digest(csv_text), csv_text, event
    )


async def load_review(user: User, event_ref: str, csv_text: str) -> LoadedReview:
    """Resolve the event through the website's read rules, then review the csv against it."""
    event = await sync_to_async(_visible_event)(user, event_ref)
    return await _review(user, event, csv_text)


async def load_cached_review(user: User, event_ref: str, review_id: str) -> LoadedReview:
    """Re-run a review on the csv this user cached for this event; refuse once it's gone."""
    event = await sync_to_async(_visible_event)(user, event_ref)
    key = review_cache_key(user.pk, str(event.id), review_id)
    csv_text = await caches["ratelimit"].aget(key)
    if csv_text is None:
        raise ToolError("review expired — run review_cashapp_payments again")
    return await _review(user, event, csv_text)


async def rerun_review(user: User, loaded: LoadedReview) -> LoadedReview:
    """Review the same csv again against the event's current rsvps."""
    return await _review(user, loaded.record, loaded.csv_text)


async def remember_csv(user: User, loaded: LoadedReview, csv_text: str) -> None:
    key = review_cache_key(user.pk, loaded.event_id, loaded.review_id)
    await caches["ratelimit"].aset(key, csv_text, REVIEW_TTL_SECONDS)


def _local(value: datetime) -> str:
    return value.astimezone(settings.COMMUNITY_TZ).isoformat()


def people_text(p: PaymentProposal) -> str | None:
    if p.people_low is None:
        return None
    if p.people_high is None:
        return f"{p.people_low}+"
    return str(p.people_low) if p.people_low == p.people_high else f"{p.people_low}-{p.people_high}"


def payment_out(p: PaymentProposal) -> dict[str, Any]:
    return {
        "payment_id": p.payment_id,
        "row": p.row_index + 1,
        "sender": p.sender_name,
        "note": p.note,
        "amount": str(p.amount),
        "paid_at": _local(p.paid_at),
    }


def payment_summary(p: PaymentProposal) -> dict[str, Any]:
    return {
        **payment_out(p),
        "confidence": p.confidence.value,
        "reason": p.reason,
        "covers_people": people_text(p),
    }


def _proposal_out(p: PaymentProposal, loaded: LoadedReview) -> dict[str, Any]:
    return {
        **payment_out(p),
        "covers_people": people_text(p),
        "reason": p.reason,
        "matched_by": p.matched_by.value,
        "guests": [loaded.person(uid) for uid in p.user_ids],
        "candidates": [loaded.person(uid) for uid in p.candidate_user_ids],
    }


def gap_out(g: GapGuest) -> dict[str, Any]:
    return {
        "user_id": g.user_id,
        "name": g.name,
        "status": g.status.value,
        "said_paid": g.said_paid,
        "reason": g.reason.value,
        "pending_payment_ids": g.pending_payment_ids,
    }


def _lead_out(lead: AmountMismatchLead, loaded: LoadedReview) -> dict[str, Any]:
    return {
        "payment_id": lead.payment_id,
        "row": lead.row_index + 1,
        "sender": lead.sender_name,
        "amount": str(lead.amount),
        "paid_at": _local(lead.paid_at),
        "guests": [loaded.person(uid) for uid in lead.user_ids],
    }


def _unreadable_out(row: UnreadableRow) -> dict[str, Any]:
    return {
        "payment_id": row.payment_id,
        "row": row.row_index + 1,
        "sender": row.sender_name,
        "amount": row.raw_amount,
        "date": row.raw_date,
    }


def _decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _price_out(price: PriceSpec, text: str) -> dict[str, Any]:
    return {
        "text": text,
        "read_as": price.kind.value,
        "low": _decimal(price.low),
        "high": _decimal(price.high),
    }


def proposals_by_confidence(loaded: LoadedReview) -> dict[MatchConfidence, list[dict[str, Any]]]:
    grouped: dict[MatchConfidence, list[dict[str, Any]]] = defaultdict(list)
    for p in loaded.review.proposals:
        grouped[p.confidence].append(_proposal_out(p, loaded))
    return grouped


def review_out(loaded: LoadedReview) -> dict[str, Any]:
    review = loaded.review
    grouped = proposals_by_confidence(loaded)
    return {
        "event": loaded.event,
        "review_id": loaded.review_id,
        "gap_list": [gap_out(g) for g in review.gap_guests],
        "counts": {
            "csv_rows": review.total_rows,
            "confident": len(grouped[MatchConfidence.CONFIDENT]),
            "unsure": len(grouped[MatchConfidence.UNSURE]),
            "unplaced": len(grouped[MatchConfidence.UNMATCHED]),
            "gap": len(review.gap_guests),
            "already_verified": len(loaded.verified),
        },
        "confident": grouped[MatchConfidence.CONFIDENT],
        "unsure": grouped[MatchConfidence.UNSURE],
        "unplaced_payments": grouped[MatchConfidence.UNMATCHED],
        "amount_mismatch_leads": [_lead_out(lead, loaded) for lead in review.amount_mismatch_leads],
        "unreadable_rows": [_unreadable_out(row) for row in review.unreadable_rows],
        "filtered_out": review.filtered,
        "price": _price_out(review.price, loaded.event["price"]),
    }
