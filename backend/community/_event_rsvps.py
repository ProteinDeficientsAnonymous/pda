import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import transaction
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from notifications.service import (
    broadcast_event_comment_update,
    notify_event_comment,
    notify_rsvp_declined_note,
    notify_rsvp_status_changed,
)

from community._event_helpers import (
    _can_edit_event,
    _event_out,
    broadcast_capacity_change,
    load_event_with_stats_prefetch,
)
from community._event_read_visibility import _enforce_event_read_visibility
from community._event_rsvp_answers import answers_required_for_status, build_rsvp_answers
from community._event_schemas import EventOut, RSVPIn
from community._rsvp_counts import _attending_headcount_db
from community._rsvp_payment import requires_payment_gate
from community._rsvp_status_emails import email_member_rsvp_status, email_promoted_users
from community._shared import ErrorOut
from community._tentative_member_access import (
    enforce_tentative_member_write_access,
    event_viewer_for,
)
from community._validation import Code, raise_validation
from community._waitlist import promote_from_waitlist
from community.models import Event, EventComment, EventRSVP, RSVPStatus

router = Router()


def _validate_rsvp_access(user, event) -> None:
    """Raise ValidationException if the user cannot RSVP on this event."""
    # Enforce read visibility first: this rejects deleted (404), invite-only the
    # caller can't see (403), and members-only-to-anon events — the same gating
    # get_event applies. Draft events the caller can merely *see* (e.g. a pending
    # cohost invitee) still must not RSVP, so guard drafts to editors below.
    _enforce_event_read_visibility(event, event_viewer_for(user, event))
    enforce_tentative_member_write_access(user, event, "rsvp_tentative_member_event")
    if event.is_draft and not _can_edit_event(user, event):
        raise_validation(Code.Event.PERM_DENIED, status_code=403, action="rsvp_draft_event")
    if not event.rsvp_enabled:
        raise_validation(Code.Event.RSVPS_NOT_ENABLED, status_code=400)
    if event.is_cancelled:
        raise_validation(Code.Event.RSVPS_CLOSED_CANCELLED, status_code=400)
    if event.is_past and not _can_edit_event(user, event):
        raise_validation(Code.Event.RSVPS_CLOSED_PAST, status_code=400)


def _resolve_rsvp_status(
    event: Event, user, requested_status: str, has_plus_one: bool
) -> tuple[str, bool]:
    """Resolve final RSVP status accounting for capacity limits.

    Returns (status, has_plus_one). Raises ValidationException if a +1 is
    denied at capacity.
    """
    # Don't trust the client: a stale/crafted +1 must not inflate a disallowed event.
    if not event.allow_plus_ones:
        has_plus_one = False

    if requested_status != RSVPStatus.ATTENDING or event.max_attendees is None:
        return requested_status, has_plus_one

    headcount = _attending_headcount_db(event, exclude_user=user)
    new_spots = 1 + (1 if has_plus_one else 0)

    if headcount + new_spots <= event.max_attendees:
        return requested_status, has_plus_one

    # Over capacity — check if user is already attending (just toggling +1)
    existing = EventRSVP.objects.filter(event=event, user=user).first()
    if existing and existing.status == RSVPStatus.ATTENDING:
        if has_plus_one:
            raise_validation(Code.Event.NO_PLUS_ONE_SPOTS, status_code=400)
        # Removing +1 is always fine
        return requested_status, has_plus_one

    # New attending RSVP (or +1 party) at capacity — waitlist the whole party.
    # Keep has_plus_one so promotion seats them together later; never drop the +1.
    return RSVPStatus.WAITLISTED, has_plus_one


def _keep_waitlist_place(event: Event, existing: EventRSVP | None, final_status: str) -> str:
    """Keep a waitlisted row waitlisted when it re-saves "going" (e.g. to add a +1).

    Only promote_from_waitlist seats people, in line order, so an edit can't
    skip whoever is ahead.
    """
    if (
        event.max_attendees is not None
        and existing is not None
        and existing.status == RSVPStatus.WAITLISTED
        and final_status == RSVPStatus.ATTENDING
    ):
        return RSVPStatus.WAITLISTED
    return final_status


def _line_may_move(existing: EventRSVP | None, final_status: str, final_plus_one: bool) -> bool:
    """Whether this change could let someone off the waitlist."""
    if existing is None:
        return False
    if existing.status == RSVPStatus.WAITLISTED:
        # Dropping a +1 or leaving the line can unblock whoever is behind.
        return True
    if existing.status != RSVPStatus.ATTENDING:
        return False
    return final_status != RSVPStatus.ATTENDING or (existing.has_plus_one and not final_plus_one)


def _validate_rsvp_status(status: str) -> None:
    """Raise ValidationException if the requested RSVP status is invalid."""
    valid_statuses = {RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.CANT_GO}
    if status == RSVPStatus.WAITLISTED or status not in valid_statuses:
        raise_validation(
            Code.Event.RSVP_INVALID_STATUS,
            field="status",
            status_code=400,
            allowed=sorted(valid_statuses),
        )


def _resolve_cancelled_at(existing: EventRSVP | None, final_status: str):
    """Timestamp the transition into CANT_GO; clear it on any other status.

    Preserves the original cancel time when a member re-saves while already
    CANT_GO (e.g. toggling +1), so lead-time reflects the first cancellation.
    """
    if final_status != RSVPStatus.CANT_GO:
        return None
    if existing is not None and existing.status == RSVPStatus.CANT_GO:
        return existing.cancelled_at
    return timezone.now()


def _resolve_pre_cancel_status(existing: EventRSVP | None, final_status: str) -> str | None:
    """Status before the first cant_go transition; cleared when leaving cant_go."""
    if final_status != RSVPStatus.CANT_GO:
        return None
    if existing is None:
        return None
    if existing.status == RSVPStatus.CANT_GO:
        return existing.pre_cancel_status
    return existing.status


def _post_rsvp_comment(event_id, user, final_status: str, comment: str | None) -> bool:
    """Post a non-empty RSVP comment: an EventComment (going/maybe) or a decline notification (can't go).

    Returns True if a decline notification was sent, so the caller can skip the
    redundant "can't go" status notification.
    """
    cleaned_comment = (comment or "").strip()
    if not cleaned_comment:
        return False
    try:
        # Fresh fetch, not the row-locked event from _apply_rsvp_in_transaction — its co_hosts
        # prefetch predates this (already-committed) transaction and could be stale.
        event = Event.objects.prefetch_related("co_hosts").get(id=event_id)
        if final_status == RSVPStatus.CANT_GO:
            notify_rsvp_declined_note(event=event, author=user, note=cleaned_comment)
            return True
        posted_comment = EventComment.objects.create(event=event, author=user, body=cleaned_comment)
        notify_event_comment(posted_comment)
        broadcast_event_comment_update(event)
        return False
    except Exception:
        # RSVP already committed — a failure here must not 500 an already-successful RSVP.
        logging.getLogger(__name__).exception(
            "rsvp_comment_post_failed", extra={"event_id": str(event_id), "user_id": str(user.pk)}
        )
        return False


def _resolve_paid_confirmed_at(
    existing: EventRSVP | None, paid_confirmed: bool, final_status: str
) -> datetime | None:
    """Preserve a standing stamp; otherwise stamp only on a confirmed attending/waitlisted write."""
    if existing is not None and existing.paid_confirmed_at is not None:
        return existing.paid_confirmed_at
    if paid_confirmed and final_status in (RSVPStatus.ATTENDING, RSVPStatus.WAITLISTED):
        return timezone.now()
    return None


def payment_audit_details(event_id, user_id) -> dict:
    """Audit fields describing the payment stamp actually stored for this rsvp.

    Read back from the row rather than echoing the request payload — a
    `paid_confirmed: true` on an already-stamped or ungated write changes
    nothing, and the audit trail has to record what happened, not what was asked.
    """
    stamped_at = (
        EventRSVP.objects.filter(event_id=event_id, user_id=user_id)
        .values_list("paid_confirmed_at", flat=True)
        .first()
    )
    return {
        "paid_confirmed": stamped_at is not None,
        "paid_confirmed_at": stamped_at.isoformat() if stamped_at else None,
    }


def _snapshot_rsvp_answers(
    event: Event,
    existing: EventRSVP | None,
    final_status: str,
    answers: dict[str, str] | None,
    *,
    require_answers: bool = True,
) -> dict:
    existing_answers = dict(existing.questionnaire_responses or {}) if existing is not None else {}
    if not answers_required_for_status(final_status) or not require_answers:
        return existing_answers

    questions = list(event.rsvp_questions.all())
    current_ids = {str(question.id) for question in questions}
    if answers is None:
        answers = {
            question_id: snapshot["answer"]
            for question_id, snapshot in existing_answers.items()
            if question_id in current_ids
        }
        build_rsvp_answers(questions, answers, require_answers=True)
        return existing_answers

    current_answers = build_rsvp_answers(questions, answers, require_answers=True)
    for question_id, snapshot in current_answers.items():
        previous = existing_answers.get(question_id)
        if previous is not None and previous["answer"] == snapshot["answer"]:
            current_answers[question_id] = previous
    historical_answers = {
        question_id: snapshot
        for question_id, snapshot in existing_answers.items()
        if question_id not in current_ids
    }
    return historical_answers | current_answers


def _rsvp_unchanged(
    existing: EventRSVP | None,
    *,
    final_status: str,
    final_plus_one: bool,
    new_confirmed_at,
    answers_snapshot: dict,
) -> bool:
    if existing is None:
        return False
    return (
        existing.status == final_status
        and existing.has_plus_one == final_plus_one
        and existing.paid_confirmed_at == new_confirmed_at
        and dict(existing.questionnaire_responses or {}) == answers_snapshot
    )


@dataclass(frozen=True, slots=True)
class _RsvpApply:
    status: str
    has_plus_one: bool = False
    paid_confirmed: bool = False
    answers: dict[str, str] | None = None
    # Host auto-rsvps bypass the payment gate and required questions.
    skip_host_gates: bool = False


def _apply_rsvp_in_transaction(
    event_id, user, rsvp: _RsvpApply
) -> tuple[str, list[str], str | None]:
    """Execute RSVP upsert inside a locked transaction.

    Returns (final_status, promoted_user_ids, previous_status). promoted_user_ids is the
    list of users promoted off the waitlist by this change (empty unless a spot
    freed); previous_status is the status read under the lock, None if there was no row.

    Raises ValidationException on failure.
    """
    # Prefetch the relations _validate_rsvp_access → _enforce_event_read_visibility
    # reads for invite-only events, so they don't fire lazy queries while the row
    # is locked under select_for_update.
    event = (
        Event.objects.select_for_update()
        .prefetch_related("co_hosts", "invited_users", "rsvp_questions")
        .get(id=event_id)
    )

    _validate_rsvp_access(user, event)

    existing = EventRSVP.objects.filter(event=event, user=user).first()
    previous_status = existing.status if existing is not None else None

    final_status, final_plus_one = _resolve_rsvp_status(event, user, rsvp.status, rsvp.has_plus_one)
    final_status = _keep_waitlist_place(event, existing, final_status)
    # Joining the waitlist is free; promotion asks the guest to pay.
    gate_exempt = rsvp.paid_confirmed or rsvp.skip_host_gates
    if not gate_exempt and requires_payment_gate(event, existing, final_status):
        raise_validation(Code.Event.PAYMENT_CONFIRMATION_REQUIRED, status_code=400)
    answers_snapshot = _snapshot_rsvp_answers(
        event, existing, final_status, rsvp.answers, require_answers=not rsvp.skip_host_gates
    )

    new_confirmed_at = _resolve_paid_confirmed_at(existing, rsvp.paid_confirmed, final_status)

    if _rsvp_unchanged(
        existing,
        final_status=final_status,
        final_plus_one=final_plus_one,
        new_confirmed_at=new_confirmed_at,
        answers_snapshot=answers_snapshot,
    ):
        return final_status, [], previous_status

    EventRSVP.objects.update_or_create(
        event=event,
        user=user,
        defaults={
            "status": final_status,
            "has_plus_one": final_plus_one,
            "cancelled_at": _resolve_cancelled_at(existing, final_status),
            "pre_cancel_status": _resolve_pre_cancel_status(existing, final_status),
            "paid_confirmed_at": new_confirmed_at,
            "questionnaire_responses": answers_snapshot,
        },
    )

    line_may_move = _line_may_move(existing, final_status, final_plus_one)
    promoted_user_ids = promote_from_waitlist(event) if line_may_move else []

    return final_status, promoted_user_ids, previous_status


@router.post(
    "/events/{event_id}/rsvp/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def upsert_rsvp(request, event_id: UUID, payload: RSVPIn):
    try:
        Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)

    _validate_rsvp_status(payload.status)

    with transaction.atomic():
        final_status, promoted_user_ids, previous_status = _apply_rsvp_in_transaction(
            event_id,
            request.auth,
            _RsvpApply(
                status=payload.status,
                has_plus_one=payload.has_plus_one,
                paid_confirmed=payload.paid_confirmed,
                answers=payload.questionnaire_responses,
            ),
        )

    sent_decline_note = _post_rsvp_comment(event_id, request.auth, final_status, payload.comment)

    audit_log(
        logging.INFO,
        "rsvp_changed",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT,
            id=str(event_id),
            details={
                "status": final_status,
                **payment_audit_details(event_id, request.auth.pk),
            },
        ),
    )
    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not sent_decline_note:
        notify_rsvp_status_changed(event, request.auth, final_status)
    # Actor already has the fresh event in this response, so exclude them.
    broadcast_capacity_change(event_id, exclude_user_ids={str(request.auth.pk)})
    if final_status != previous_status:
        email_member_rsvp_status(request, event, request.auth, final_status)
    email_promoted_users(request, event, promoted_user_ids)
    return Status(200, _event_out(event, request.auth))


@router.delete(
    "/events/{event_id}/rsvp/",
    response={204: None, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def delete_rsvp(request, event_id: UUID):
    try:
        Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)

    with transaction.atomic():
        event, promoted_user_ids = _delete_rsvp_in_transaction(event_id, request.auth)

    audit_log(
        logging.INFO,
        "rsvp_deleted",
        request,
        target=AuditTarget(type=AuditTargetType.EVENT, id=str(event_id)),
    )
    email_promoted_users(request, event, promoted_user_ids)
    return Status(204, None)


def _validate_rsvp_delete_access(event: Event, user) -> None:
    """Raise ValidationException if the user cannot withdraw their RSVP."""
    # No standing RSVP: don't let a caller probe an event they can't read. An
    # existing RSVP-holder skips the read-visibility gate so they can withdraw
    # even if the event later turned invite-only / draft and excluded them —
    # their stale RSVP would otherwise be unremovable while still counting
    # toward the headcount. (The cancelled / past freezes still apply.)
    _enforce_event_read_visibility(event, event_viewer_for(user, event))
    enforce_tentative_member_write_access(user, event, "rsvp_tentative_member_event")
    if event.is_draft and not _can_edit_event(user, event):
        raise_validation(Code.Event.PERM_DENIED, status_code=403, action="rsvp_draft_event")
    raise_validation(Code.Event.RSVP_NOT_FOUND, status_code=404)


def _delete_rsvp_in_transaction(event_id, user) -> tuple[Event, list[str]]:
    """Delete the user's RSVP inside a locked transaction.

    Returns (event, promoted_user_ids). promoted_user_ids is empty unless a
    spot freed, surfaced so the caller can email promoted users after commit.

    Raises ValidationException on failure.
    """
    event = (
        Event.objects.select_for_update()
        .prefetch_related("co_hosts", "invited_users", "rsvp_questions")
        .get(id=event_id)
    )
    if event.is_deleted:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    rsvp = EventRSVP.objects.filter(event=event, user=user).first()
    if not rsvp:
        _validate_rsvp_delete_access(event, user)
    if event.is_cancelled:
        raise_validation(Code.Event.RSVPS_CLOSED_CANCELLED, status_code=400)
    if event.is_past and not _can_edit_event(user, event):
        raise_validation(Code.Event.RSVPS_CLOSED_PAST, status_code=400)

    was_attending = rsvp.status == RSVPStatus.ATTENDING
    rsvp.delete()
    if not was_attending:
        return event, []

    promoted_user_ids = promote_from_waitlist(event)
    broadcast_capacity_change(event_id, exclude_user_ids={str(user.pk)})
    return event, promoted_user_ids
