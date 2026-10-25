from collections import defaultdict
from typing import Annotated, Any
from uuid import UUID

from community._cashapp_import_types import MatchConfidence, PaymentProposal
from community._event_host_rsvps import verify_guest_payments as verify_guest_payments_view
from community._event_schemas import MAX_BULK_PAYMENT_VERIFY, BulkPaymentVerifyIn
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from mcp_gateway.cashapp_review import (
    LoadedReview,
    gap_out,
    load_cached_review,
    load_review,
    payment_summary,
    proposals_by_confidence,
)
from mcp_gateway.confirm import Confirmed, issue_confirm_token, use_confirm_token
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.tools.payments_review import EventRef
from mcp_gateway.view_calls import call_view

_BY_HAND = "a host can verify that guest by hand in the app"

ReviewId = Annotated[
    str, Field(pattern=r"^[0-9a-f]{64}$", description="review_id from review_cashapp_payments")
]


class PaymentAssignment(BaseModel):
    payment_id: str = Field(min_length=1, max_length=200, description="from the review")
    user_ids: list[UUID] = Field(
        min_length=1,
        max_length=50,
        description="guests this payment covers, from that payment's guests or candidates",
    )


def _not_a_proposal(pid: str, loaded: LoadedReview) -> ToolError:
    review = loaded.review
    if any(lead.payment_id == pid for lead in review.amount_mismatch_leads):
        return ToolError(
            f"payment {pid} is an amount mismatch lead (its amount doesn't fit the price), so it "
            f"can't be applied here; {_BY_HAND}"
        )
    if any(row.payment_id == pid for row in review.unreadable_rows):
        return ToolError(f"payment {pid} couldn't be read, so it can't be applied here; {_BY_HAND}")
    return ToolError(f"payment {pid} isn't in this review for the event")


def _check_headcount(proposal: PaymentProposal, user_ids: list[str], loaded: LoadedReview) -> None:
    headcount = sum(loaded.guests[uid].headcount for uid in user_ids)
    if proposal.people_high is not None and headcount > proposal.people_high:
        raise ToolError(
            f"payment {proposal.payment_id} (${proposal.amount}) covers at most "
            f"{proposal.people_high} people, but these guests are {headcount} with plus-ones; "
            "assign fewer guests to it"
        )


def _assignment_user_ids(assignment: PaymentAssignment, loaded: LoadedReview) -> list[str]:
    pid = assignment.payment_id
    proposal = next((p for p in loaded.review.proposals if p.payment_id == pid), None)
    if proposal is None:
        raise _not_a_proposal(pid, loaded)
    if proposal.confidence == MatchConfidence.UNMATCHED:
        raise ToolError(f"payment {pid} didn't match any guest, so it can't be applied; {_BY_HAND}")
    allowed = set(proposal.user_ids) | set(proposal.candidate_user_ids)
    user_ids = [str(uid) for uid in assignment.user_ids]
    outside = [uid for uid in user_ids if uid not in allowed]
    if outside:
        raise ToolError(
            f"payment {pid} can only verify its matched guests or candidates "
            f"({', '.join(sorted(allowed))}), not {', '.join(outside)}"
        )
    _check_headcount(proposal, user_ids, loaded)
    return user_ids


def _selection(assignments: list[PaymentAssignment], loaded: LoadedReview) -> dict[str, list[str]]:
    """return(dict): each assigned guest's user id -> sorted payment ids covering them."""
    payment_ids = [a.payment_id for a in assignments]
    if len(set(payment_ids)) != len(payment_ids):
        raise ToolError("list each payment_id once, with every guest it covers")
    covered: dict[str, list[str]] = defaultdict(list)
    for assignment in assignments:
        for uid in _assignment_user_ids(assignment, loaded):
            covered[uid].append(assignment.payment_id)
    return {uid: sorted(set(pids)) for uid, pids in sorted(covered.items())}


def _to_verify(selection: dict[str, list[str]], loaded: LoadedReview) -> dict[str, list[str]]:
    pending = {uid: pids for uid, pids in selection.items() if uid not in loaded.verified}
    if not pending:
        raise ToolError("everyone in these assignments is already verified; nothing to do")
    if len(pending) > MAX_BULK_PAYMENT_VERIFY:
        raise ToolError(f"verify at most {MAX_BULK_PAYMENT_VERIFY} guests at a time")
    return pending


def _preview(
    loaded: LoadedReview, selection: dict[str, list[str]], pending: dict[str, list[str]], token: str
) -> dict[str, Any]:
    payments = {p.payment_id: payment_summary(p) for p in loaded.review.proposals}
    to_verify = [
        {
            **loaded.person(uid),
            "said_paid": loaded.guests[uid].said_paid,
            "payments": [payments[pid] for pid in pids],
        }
        for uid, pids in pending.items()
    ]
    return {
        "event": loaded.event,
        "to_verify": sorted(to_verify, key=lambda g: (g["name"] or "").lower()),
        "already_verified": [loaded.person(uid) for uid in selection if uid not in pending],
        "confirm_token": token,
    }


def _bound(
    user_pk: Any, loaded: LoadedReview, selection: dict[str, list[str]], pending: dict
) -> Confirmed:
    # Only the selected guests' verified state matters; unrelated verifications don't stale it.
    selected_verified = sorted(uid for uid in selection if uid in loaded.verified)
    state = [loaded.review_id, selected_verified]
    return Confirmed(user_pk, loaded.event_id, "verify_payments", pending, state)


async def _apply(user: Any, loaded: LoadedReview, pending: dict[str, list[str]]) -> dict[str, Any]:
    payload = BulkPaymentVerifyIn(user_ids=[UUID(uid) for uid in pending])
    result = await call_view(
        verify_guest_payments_view, user, event_id=UUID(loaded.event_id), payload=payload
    )
    after = await load_review(user, loaded.event_id, loaded.csv_text)
    grouped = proposals_by_confidence(after)
    return {
        "event": after.event,
        "verified": [after.person(uid) for uid in result["verified_user_ids"]],
        "already_verified": [after.person(uid) for uid in result["already_verified_user_ids"]],
        "event_verified_total": result["event_verified_total"],
        "gap_list": [gap_out(g) for g in after.review.gap_guests],
        "unplaced_payments": grouped[MatchConfidence.UNMATCHED],
    }


@pda_tool(
    PermissionKey.IMPORT_PAYMENTS,
    description=(
        "mark guests' payments host-verified, after review_cashapp_payments. send the event, the "
        "review_id, and assignments: each confident or unsure payment_id the user approved with "
        "the user_ids it pays for, picked from that payment's guests or candidates (plus-ones "
        "count toward what a payment covers). unplaced payments, amount mismatch leads and "
        "unreadable rows can't be applied: a host verifies those guests by hand in the app. the "
        "first call saves nothing and returns to_verify (each guest with the payment covering "
        "them) and a confirm_token: show that list, get an explicit yes, then call again with the "
        "same arguments and the token. returns who was verified and the updated gap_list."
    ),
)
async def verify_cashapp_payments(
    event: EventRef,
    review_id: ReviewId,
    assignments: Annotated[list[PaymentAssignment], Field(min_length=1, max_length=500)],
    confirm_token: Annotated[
        str | None, Field(description="from the preview; send only after the user said yes")
    ] = None,
) -> dict[str, Any]:
    user = await current_user()
    loaded = await load_cached_review(user, event, review_id)
    selection = _selection(assignments, loaded)
    pending = _to_verify(selection, loaded)
    bound = _bound(user.pk, loaded, selection, pending)
    if confirm_token is None:
        return _preview(loaded, selection, pending, issue_confirm_token(bound))
    await use_confirm_token(confirm_token, bound)
    return await _apply(user, loaded, pending)
