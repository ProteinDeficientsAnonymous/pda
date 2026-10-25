from collections import Counter
from dataclasses import dataclass, replace

from community._cashapp_import_filter import KeptPayment
from community._cashapp_import_names import NameIndex
from community._cashapp_import_price import PeopleRange
from community._cashapp_import_types import (
    AmountMismatchLead,
    GuestRecord,
    MatchConfidence,
    MatchSource,
    PaymentProposal,
)
from community.models import RSVPStatus

MATCHABLE_STATUSES = frozenset({RSVPStatus.ATTENDING, RSVPStatus.WAITLISTED})


@dataclass(frozen=True)
class _Hits:
    senders: list[GuestRecord]
    note_guests: list[GuestRecord]
    note_ambiguous: list[GuestRecord]
    weak: list[GuestRecord]
    sender_by_nickname: bool = False


@dataclass(frozen=True)
class _Pick:
    covered: list[GuestRecord]
    candidates: list[GuestRecord]
    source: MatchSource
    reason: str
    forced_unsure: bool = False


def _unique(guests: list[GuestRecord]) -> list[GuestRecord]:
    return list({g.user_id: g for g in guests}.values())


def _split_hits(
    hits: dict[str, list[GuestRecord]], exclude: set[str]
) -> tuple[list[GuestRecord], list[GuestRecord]]:
    """return(tuple): (guests named unambiguously, guests sharing a name with someone else)."""
    clear, ambiguous = [], []
    for guests in hits.values():
        remaining = [g for g in guests if g.user_id not in exclude]
        (clear if len(guests) == 1 else ambiguous).extend(remaining)
    return _unique(clear), _unique(ambiguous)


def _find_hits(sender_name: str, note: str, index: NameIndex) -> _Hits:
    senders, by_nickname = index.sender_matches(sender_name)
    sender_ids = {g.user_id for g in senders}
    full_hits, single_hits = index.note_hits(note)
    note_guests, note_ambiguous = _split_hits(full_hits, sender_ids)
    named = sender_ids | {g.user_id for g in note_guests + note_ambiguous}
    weak = _unique([g for gs in single_hits.values() for g in gs if g.user_id not in named])
    return _Hits(senders, note_guests, note_ambiguous, weak, by_nickname)


def _pick_without_sender(hits: _Hits) -> _Pick:
    extras = hits.note_ambiguous + hits.weak
    if hits.note_guests and extras:
        return _Pick(
            hits.note_guests, extras, MatchSource.NOTE, "note also names another guest", True
        )
    if hits.note_guests:
        return _Pick(hits.note_guests, [], MatchSource.NOTE, "note names the guest")
    if hits.note_ambiguous:
        return _Pick([], extras, MatchSource.NOTE, "note name matches several guests", True)
    if hits.weak:
        return _Pick([], extras, MatchSource.NOTE, "only a first name in the note matched", True)
    return _Pick([], [], MatchSource.NONE, "no guest matches the sender or note", True)


def _pick_attending_sender(sender: GuestRecord, hits: _Hits) -> _Pick:
    extras = hits.note_ambiguous + hits.weak
    source = MatchSource.SENDER_AND_NOTE if hits.note_guests else MatchSource.SENDER
    covered = [sender, *hits.note_guests]
    if hits.sender_by_nickname:
        return _Pick(covered, extras, source, "only a nickname matched the sender", True)
    if extras:
        return _Pick(covered, extras, source, "note also names another guest", True)
    return _Pick(covered, [], source, "sender name matches")


def _pick(hits: _Hits) -> _Pick:
    """Sender first; the note decides when the sender isn't an attending guest."""
    extras = hits.note_ambiguous + hits.weak
    if len(hits.senders) > 1:
        candidates = hits.senders + hits.note_guests + extras
        return _Pick([], candidates, MatchSource.SENDER, "sender name matches several guests", True)
    sender = hits.senders[0] if hits.senders else None
    if sender and sender.status == RSVPStatus.ATTENDING:
        return _pick_attending_sender(sender, hits)
    if sender and not hits.note_guests:
        return _Pick([sender], extras, MatchSource.SENDER, "guest is waitlisted", True)
    pick = _pick_without_sender(hits)
    return replace(pick, candidates=pick.candidates + hits.senders)


def _people_text(people: PeopleRange) -> str:
    if people.low == people.high:
        return "1 person" if people.low == 1 else f"{people.low} people"
    return f"{people.low}-{people.high} people"


def _headcount_reason(covered: list[GuestRecord], people: PeopleRange) -> str | None:
    if any(g.status != RSVPStatus.ATTENDING for g in covered):
        return "a matched guest is waitlisted"
    headcount = sum(g.headcount for g in covered)
    if not people.includes(headcount):
        return f"amount covers {_people_text(people)}, matched {headcount}"
    if len(covered) > 1 and people.low != people.high:
        return f"amount could cover {_people_text(people)}"
    return None


def _unsure_reason(pick: _Pick, payment: KeptPayment) -> str | None:
    if pick.forced_unsure:
        return pick.reason
    if payment.refunded:
        return "refunded?"
    if payment.people is None:
        return "price couldn't be read"
    return _headcount_reason(pick.covered, payment.people)


def _confidence(pick: _Pick, unsure: str | None) -> MatchConfidence:
    if not pick.covered and not pick.candidates:
        return MatchConfidence.UNMATCHED
    return MatchConfidence.UNSURE if unsure else MatchConfidence.CONFIDENT


def propose_match(payment: KeptPayment, index: NameIndex) -> PaymentProposal:
    row = payment.row
    pick = _pick(_find_hits(row.sender_name, row.note, index))
    unsure = _unsure_reason(pick, payment)
    confidence = _confidence(pick, unsure)
    candidates = [] if confidence == MatchConfidence.CONFIDENT else pick.candidates
    return PaymentProposal(
        payment_id=row.payment_id,
        row_index=row.row_index,
        sender_name=row.sender_name,
        note=row.note,
        amount=payment.amount,
        paid_at=payment.paid_at,
        confidence=confidence,
        reason=unsure or pick.reason,
        matched_by=pick.source,
        user_ids=[g.user_id for g in pick.covered],
        candidate_user_ids=[g.user_id for g in candidates],
        people_low=payment.people.low if payment.people else None,
        people_high=payment.people.high if payment.people else None,
    )


def _flag_shared_guests(proposals: list[PaymentProposal]) -> list[PaymentProposal]:
    counts = Counter(uid for p in proposals for uid in p.user_ids)
    shared = {uid for uid, n in counts.items() if n > 1}
    return [
        replace(p, confidence=MatchConfidence.UNSURE, reason="guest also matched another payment")
        if p.confidence == MatchConfidence.CONFIDENT and shared.intersection(p.user_ids)
        else p
        for p in proposals
    ]


def match_payments(kept: list[KeptPayment], guests: list[GuestRecord]) -> list[PaymentProposal]:
    index = NameIndex.build([g for g in guests if g.status in MATCHABLE_STATUSES])
    return _flag_shared_guests([propose_match(p, index) for p in kept])


def amount_mismatch_leads(
    mismatches: list[KeptPayment], guests: list[GuestRecord]
) -> list[AmountMismatchLead]:
    index = NameIndex.build([g for g in guests if g.status in MATCHABLE_STATUSES])
    leads = []
    for payment in mismatches:
        senders, _ = index.sender_matches(payment.row.sender_name)
        if senders:
            leads.append(
                AmountMismatchLead(
                    payment_id=payment.row.payment_id,
                    row_index=payment.row.row_index,
                    sender_name=payment.row.sender_name,
                    amount=payment.amount,
                    paid_at=payment.paid_at,
                    user_ids=[g.user_id for g in senders],
                )
            )
    return leads
