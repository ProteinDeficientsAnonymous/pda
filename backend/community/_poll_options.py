"""EventPoll option mutation endpoints — add, update, delete."""

import logging
from uuid import UUID

from config.audit import audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from ninja import Router
from ninja.responses import Status

from community._event_poll_schemas import EventPollOut, PollOptionIn
from community._polls import (
    _can_manage_poll,
    _duplicate_option_time_guard,
    _poll_out,
    _validate_poll_options,
)
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event, EventPoll, EventStatus, PollOption

router = Router()


def _get_active_poll(user, event_id: UUID) -> tuple[Event, EventPoll]:
    """Return (event, poll) for poll option mutations. Raises on failure."""
    try:
        event = Event.objects.prefetch_related("co_hosts").get(id=event_id)
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_manage_poll(user, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_poll_option")
    if event.status == EventStatus.CANCELLED:
        raise_validation(Code.Event.CANCELLED_CANNOT_BE_EDITED, status_code=400)
    try:
        poll = (
            EventPoll.objects.select_related("winning_option")
            .prefetch_related("options__votes__user")
            .get(event=event)
        )
    except EventPoll.DoesNotExist:
        raise_validation(Code.Poll.NOT_FOUND, status_code=404)
    if poll.winning_option_id is not None:
        raise_validation(Code.Poll.CANNOT_MODIFY_FINALIZED, status_code=400)
    return event, poll


@router.post(
    "/events/{event_id}/poll/options/",
    response={201: EventPollOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/h")
def add_poll_option(request, event_id: UUID, payload: PollOptionIn):
    _, poll = _get_active_poll(request.auth, event_id)
    _validate_poll_options([payload.datetime], require_at_least_one=False)
    next_order = poll.options.count()
    with _duplicate_option_time_guard():
        PollOption.objects.create(poll=poll, datetime=payload.datetime, display_order=next_order)
    audit_log(
        logging.INFO,
        "poll_option_added",
        request,
        target_type="event_poll",
        target_id=str(poll.id),
        details={"event_id": str(event_id)},
    )
    poll_fresh = (
        EventPoll.objects.select_related("winning_option")
        .prefetch_related("options__votes__user")
        .get(pk=poll.pk)
    )
    return Status(201, _poll_out(poll_fresh, request.auth))


@router.patch(
    "/events/{event_id}/poll/options/{option_id}/",
    response={200: EventPollOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/h")
def update_poll_option(request, event_id: UUID, payload: PollOptionIn, option_id: UUID):
    _, poll = _get_active_poll(request.auth, event_id)
    _validate_poll_options([payload.datetime], require_at_least_one=False)
    try:
        option = poll.options.get(id=option_id)
    except PollOption.DoesNotExist:
        raise_validation(Code.Poll.OPTION_NOT_FOUND, status_code=404)
    with _duplicate_option_time_guard():
        option.datetime = payload.datetime
        option.save(update_fields=["datetime"])
    audit_log(
        logging.INFO,
        "poll_option_updated",
        request,
        target_type="event_poll",
        target_id=str(poll.id),
        details={"event_id": str(event_id), "option_id": str(option_id)},
    )
    poll_fresh = (
        EventPoll.objects.select_related("winning_option")
        .prefetch_related("options__votes__user")
        .get(pk=poll.pk)
    )
    return Status(200, _poll_out(poll_fresh, request.auth))


@router.delete(
    "/events/{event_id}/poll/options/{option_id}/",
    response={200: EventPollOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/h")
def delete_poll_option(request, event_id: UUID, option_id: UUID):
    _, poll = _get_active_poll(request.auth, event_id)
    try:
        option = poll.options.get(id=option_id)
    except PollOption.DoesNotExist:
        raise_validation(Code.Poll.OPTION_NOT_FOUND, status_code=404)
    if poll.options.count() <= 2:
        raise_validation(Code.Poll.MIN_TWO_OPTIONS, status_code=400)
    option.delete()
    audit_log(
        logging.INFO,
        "poll_option_deleted",
        request,
        target_type="event_poll",
        target_id=str(poll.id),
        details={"event_id": str(event_id), "option_id": str(option_id)},
    )
    poll_fresh = (
        EventPoll.objects.select_related("winning_option")
        .prefetch_related("options__votes__user")
        .get(pk=poll.pk)
    )
    return Status(200, _poll_out(poll_fresh, request.auth))
