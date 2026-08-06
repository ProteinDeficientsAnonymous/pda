import logging
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
    _event_out,
    broadcast_capacity_change,
    load_event_with_stats_prefetch,
    promote_from_waitlist,
)
from community._event_rsvp_answers import answers_required_for_status, build_rsvp_answers
from community._event_schemas import EventOut, RSVPIn
from community._events import _can_edit_event, _enforce_event_read_visibility
from community._public_rsvp_shared import _email_promoted_non_members
from community._rsvp_counts import _attending_headcount_db
from community._rsvp_payment import requires_payment_gate
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event, EventComment, EventRSVP, RSVPStatus

router = Router()


def _validate_rsvp_access(user, event) -> None:
    """Raise ValidationException if the user cannot RSVP on this event."""
    # Enforce read visibility first: this rejects deleted (404), invite-only the
    # caller can't see (403), and members-only-to-anon events — the same gating
    # get_event applies. Draft events the caller can merely *see* (e.g. a pending
    # cohost invitee) still must not RSVP, so guard drafts to editors below.
    _enforce_event_read_visibility(event, user)
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
) -> dict:
    existing_answers = dict(existing.answers or {}) if existing is not None else {}
    if not answers_required_for_status(final_status):
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
        and dict(existing.answers or {}) == answers_snapshot
    )


def _apply_rsvp_in_transaction(  # noqa: PLR0913
    event_id,
    user,
    status: str,
    has_plus_one: bool,
    paid_confirmed: bool = False,
    answers: dict[str, str] | None = None,
) -> tuple[str, list[str], bool]:
    """Execute RSVP upsert inside a locked transaction.

    Returns (final_status, promoted_user_ids, created). promoted_user_ids is the
    list of users promoted off the waitlist by this change (empty unless a spot
    freed); created is True when this call created the user's first RSVP row.

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
    created = existing is None

    # Gate on the *requested* status, not the post-capacity one — else it slips through unconfirmed.
    if not paid_confirmed and requires_payment_gate(event, existing, status):
        raise_validation(Code.Event.PAYMENT_CONFIRMATION_REQUIRED, status_code=400)

    final_status, final_plus_one = _resolve_rsvp_status(event, user, status, has_plus_one)
    answers_snapshot = _snapshot_rsvp_answers(event, existing, final_status, answers)

    was_attending = existing is not None and existing.status == RSVPStatus.ATTENDING
    had_plus_one = existing is not None and existing.has_plus_one
    new_confirmed_at = _resolve_paid_confirmed_at(existing, paid_confirmed, final_status)

    if _rsvp_unchanged(
        existing,
        final_status=final_status,
        final_plus_one=final_plus_one,
        new_confirmed_at=new_confirmed_at,
        answers_snapshot=answers_snapshot,
    ):
        return final_status, [], False

    EventRSVP.objects.update_or_create(
        event=event,
        user=user,
        defaults={
            "status": final_status,
            "has_plus_one": final_plus_one,
            "cancelled_at": _resolve_cancelled_at(existing, final_status),
            "paid_confirmed_at": new_confirmed_at,
            "answers": answers_snapshot,
        },
    )

    spot_freed = (was_attending and final_status != RSVPStatus.ATTENDING) or (
        was_attending and had_plus_one and not final_plus_one
    )
    promoted_user_ids = promote_from_waitlist(event) if spot_freed else []

    return final_status, promoted_user_ids, created


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
        final_status, promoted_user_ids, _created = _apply_rsvp_in_transaction(
            event_id,
            request.auth,
            payload.status,
            payload.has_plus_one,
            payload.paid_confirmed,
            payload.answers,
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
    _email_promoted_non_members(request, event, promoted_user_ids)
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
    _email_promoted_non_members(request, event, promoted_user_ids)
    return Status(204, None)


def _validate_rsvp_delete_access(event: Event, user) -> None:
    """Raise ValidationException if the user cannot withdraw their RSVP."""
    # No standing RSVP: don't let a caller probe an event they can't read. An
    # existing RSVP-holder skips the read-visibility gate so they can withdraw
    # even if the event later turned invite-only / draft and excluded them —
    # their stale RSVP would otherwise be unremovable while still counting
    # toward the headcount. (The cancelled / past freezes still apply.)
    _enforce_event_read_visibility(event, user)
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
