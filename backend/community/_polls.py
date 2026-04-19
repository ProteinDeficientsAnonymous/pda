"""EventPoll endpoints — create, vote, finalize, delete."""

import logging
from uuid import UUID

from config.audit import audit_log
from config.media_proxy import media_path
from config.ratelimit import rate_limit
from django.db import transaction
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from users.permissions import PermissionKey

from community._event_poll_schemas import (
    EventPollFinalizeIn,
    EventPollIn,
    EventPollOptionOut,
    EventPollOut,
    EventPollVoteIn,
    PollOptionIn,
    VoterOut,
)
from community._shared import ErrorOut, _authenticated_user, _optional_jwt
from community.models import (
    Event,
    EventPoll,
    EventRSVP,
    EventStatus,
    PollAvailability,
    PollOption,
    PollVote,
    RSVPStatus,
)

router = Router()


def _can_manage_poll(user, event: Event) -> bool:
    if user.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    if user.has_permission(PermissionKey.MANAGE_SURVEYS):
        return True
    if event.created_by_id == user.pk:
        return True
    if event.co_hosts.filter(pk=user.pk).exists():
        return True
    return False


def _voter_out(user) -> VoterOut:
    return VoterOut(
        user_id=str(user.pk),
        name=user.display_name or user.phone_number,
        photo_url=media_path(user.profile_photo),
    )


def _option_out(option: PollOption, my_votes: dict[str, str]) -> EventPollOptionOut:
    votes = list(option.votes.select_related("user").all())
    yes_voters = [_voter_out(v.user) for v in votes if v.availability == PollAvailability.YES]
    maybe_voters = [_voter_out(v.user) for v in votes if v.availability == PollAvailability.MAYBE]
    no_voters = [_voter_out(v.user) for v in votes if v.availability == PollAvailability.NO]
    return EventPollOptionOut(
        id=str(option.id),
        datetime=option.datetime,
        display_order=option.display_order,
        yes_count=len(yes_voters),
        maybe_count=len(maybe_voters),
        no_count=len(no_voters),
        yes_voters=yes_voters,
        maybe_voters=maybe_voters,
        no_voters=no_voters,
    )


def _build_my_votes(options, auth_user) -> dict[str, str]:
    my_votes: dict[str, str] = {}
    for opt in options:
        for vote in opt.votes.all():
            if vote.user_id == auth_user.pk:
                my_votes[str(opt.id)] = vote.availability
                break
    return my_votes


def _poll_out(poll: EventPoll, requesting_user=None) -> EventPollOut:
    auth_user = _authenticated_user(requesting_user)
    options = list(poll.options.prefetch_related("votes__user").all())
    my_votes = _build_my_votes(options, auth_user) if auth_user is not None else {}
    winning_option = poll.winning_option
    return EventPollOut(
        id=str(poll.id),
        event_id=str(poll.event_id),  # ty: ignore[unresolved-attribute]
        is_active=poll.is_active,
        options=[_option_out(opt, my_votes) for opt in options],
        winning_option_id=str(winning_option.id) if winning_option else None,
        winning_datetime=winning_option.datetime if winning_option else None,
        finalized_by_id=str(poll.finalized_by_id) if poll.finalized_by_id else None,
        finalized_at=poll.finalized_at,
        my_votes=my_votes,
    )


@router.post(
    "/events/{event_id}/poll/",
    response={201: EventPollOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/h")
def create_event_poll(request, event_id: UUID, payload: EventPollIn):
    try:
        event = Event.objects.prefetch_related("co_hosts").get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))
    if not _can_manage_poll(request.auth, event):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "create_event_poll"},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    if event.status == EventStatus.CANCELLED:
        return Status(400, ErrorOut(detail="Cancelled events cannot be edited."))
    if hasattr(event, "poll"):
        return Status(400, ErrorOut(detail="This event already has a poll."))
    # Intentional: we accept a single-option poll here. The frontend requires ≥2
    # options on creation, but scripts/imports may legitimately start with one.
    if len(payload.options) < 1:
        return Status(400, ErrorOut(detail="A poll requires at least 1 option."))
    with transaction.atomic():
        poll = EventPoll.objects.create(event=event, created_by=request.auth)
        for i, dt in enumerate(payload.options):
            PollOption.objects.create(poll=poll, datetime=dt, display_order=i)
        # While a poll is active, the poll is the source of truth for when. Clear
        # any previously set start/end so the event can't have a stale time that
        # doesn't match any poll option.
        event.start_datetime = None
        event.end_datetime = None
        event.datetime_tbd = True
        event.save(update_fields=["start_datetime", "end_datetime", "datetime_tbd"])
    poll.refresh_from_db()
    audit_log(
        logging.INFO,
        "poll_created",
        request,
        target_type="event_poll",
        target_id=str(poll.id),
        details={"event_id": str(event_id), "option_count": len(payload.options)},
    )
    return Status(201, _poll_out(poll, request.auth))


@router.get(
    "/events/{event_id}/poll/",
    response={200: EventPollOut, 404: ErrorOut},
    auth=_optional_jwt,
)
def get_event_poll(request, event_id: UUID):
    try:
        poll = (
            EventPoll.objects.select_related("winning_option")
            .prefetch_related("options__votes__user")
            .get(event_id=event_id)
        )
    except EventPoll.DoesNotExist:
        return Status(404, ErrorOut(detail="Poll not found."))
    auth_user = _authenticated_user(request.auth)
    return Status(200, _poll_out(poll, auth_user))


@router.post(
    "/events/{event_id}/poll/vote/",
    response={200: EventPollOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def vote_on_event_poll(request, event_id: UUID, payload: EventPollVoteIn):
    try:
        poll = (
            EventPoll.objects.select_related("winning_option", "event")
            .prefetch_related("options__votes__user")
            .get(event_id=event_id, is_active=True)
        )
    except EventPoll.DoesNotExist:
        return Status(404, ErrorOut(detail="Active poll not found."))
    if poll.event.status == EventStatus.CANCELLED:
        return Status(400, ErrorOut(detail="Cancelled events cannot be edited."))
    for availability in payload.votes.values():
        if availability not in PollAvailability.VALID:
            return Status(
                400,
                ErrorOut(
                    detail=f'Invalid availability "{availability}" — must be "yes", "maybe", or "no".'
                ),
            )
    option_ids = {str(pk) for pk in poll.options.values_list("id", flat=True)}
    for option_id in payload.votes:
        if option_id not in option_ids:
            return Status(400, ErrorOut(detail=f'Option "{option_id}" not found in this poll.'))
    with transaction.atomic():
        # Remove votes for options no longer in the payload (user retracted)
        PollVote.objects.filter(
            option__poll=poll,
            user=request.auth,
        ).exclude(option_id__in=list(payload.votes.keys())).delete()
        for option_id, availability in payload.votes.items():
            option = poll.options.get(id=option_id)
            PollVote.objects.update_or_create(
                option=option,
                user=request.auth,
                defaults={"availability": availability},
            )
    audit_log(
        logging.INFO,
        "poll_vote",
        request,
        target_type="event_poll",
        target_id=str(poll.id),
        details={"event_id": str(event_id)},
    )
    poll.refresh_from_db()
    poll_fresh = (
        EventPoll.objects.select_related("winning_option")
        .prefetch_related("options__votes__user")
        .get(pk=poll.pk)
    )
    return Status(200, _poll_out(poll_fresh, request.auth))


@router.post(
    "/events/{event_id}/poll/finalize/",
    response={200: EventPollOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/h")
def finalize_event_poll(request, event_id: UUID, payload: EventPollFinalizeIn):
    try:
        event = Event.objects.prefetch_related("co_hosts").get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))
    if not _can_manage_poll(request.auth, event):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "finalize_event_poll"},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    if event.status == EventStatus.CANCELLED:
        return Status(400, ErrorOut(detail="Cancelled events cannot be edited."))
    poll, winning_option, err = _get_poll_and_option(event, payload.winning_option_id)
    if err is not None:
        return err
    with transaction.atomic():
        from django.utils import timezone

        poll.winning_option = winning_option
        poll.finalized_by = request.auth
        poll.finalized_at = timezone.now()
        poll.is_active = False
        poll.save(update_fields=["winning_option", "finalized_by", "finalized_at", "is_active"])
        event.start_datetime = winning_option.datetime
        event.datetime_tbd = False
        event.save(update_fields=["start_datetime", "datetime_tbd"])
        yes_voter_ids = winning_option.votes.filter(availability=PollAvailability.YES).values_list(
            "user_id", flat=True
        )
        for user_id in yes_voter_ids:
            EventRSVP.objects.update_or_create(
                event=event,
                user_id=user_id,
                defaults={"status": RSVPStatus.ATTENDING},
            )
    audit_log(
        logging.INFO,
        "poll_finalized",
        request,
        target_type="event_poll",
        target_id=str(poll.id),
        details={
            "event_id": str(event_id),
            "winning_datetime": winning_option.datetime.isoformat(),
        },
    )
    poll_fresh = (
        EventPoll.objects.select_related("winning_option")
        .prefetch_related("options__votes__user")
        .get(pk=poll.pk)
    )
    return Status(200, _poll_out(poll_fresh, request.auth))


@router.delete(
    "/events/{event_id}/poll/",
    response={204: None, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/h")
def delete_event_poll(request, event_id: UUID):
    try:
        event = Event.objects.prefetch_related("co_hosts").get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))
    if not _can_manage_poll(request.auth, event):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "delete_event_poll"},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        poll = EventPoll.objects.get(event=event)
    except EventPoll.DoesNotExist:
        return Status(404, ErrorOut(detail="Poll not found."))
    poll_id = str(poll.id)
    poll.delete()
    audit_log(
        logging.INFO,
        "poll_deleted",
        request,
        target_type="event_poll",
        target_id=poll_id,
        details={"event_id": str(event_id)},
    )
    return Status(204, None)


def _get_active_poll(user, event_id: UUID):
    """Return (event, poll, error_response) for poll option mutations."""
    try:
        event = Event.objects.prefetch_related("co_hosts").get(id=event_id)
    except Event.DoesNotExist:
        return None, None, Status(404, ErrorOut(detail="Event not found."))
    if not _can_manage_poll(user, event):
        return None, None, Status(403, ErrorOut(detail="Permission denied."))
    if event.status == EventStatus.CANCELLED:
        return None, None, Status(400, ErrorOut(detail="Cancelled events cannot be edited."))
    try:
        poll = (
            EventPoll.objects.select_related("winning_option")
            .prefetch_related("options__votes__user")
            .get(event=event)
        )
    except EventPoll.DoesNotExist:
        return None, None, Status(404, ErrorOut(detail="Poll not found."))
    if poll.winning_option_id is not None:
        return None, None, Status(400, ErrorOut(detail="Cannot modify a finalized poll."))
    return event, poll, None


def _get_poll_and_option(event, winning_option_id):
    """Return (poll, winning_option, error) for finalize_event_poll."""
    try:
        poll = (
            EventPoll.objects.select_related("winning_option")
            .prefetch_related("options__votes__user")
            .get(event=event)
        )
    except EventPoll.DoesNotExist:
        return None, None, Status(404, ErrorOut(detail="Poll not found."))
    if poll.winning_option_id is not None:
        return None, None, Status(400, ErrorOut(detail="This poll has already been finalized."))
    try:
        winning_option = poll.options.get(id=winning_option_id)
    except PollOption.DoesNotExist:
        return None, None, Status(400, ErrorOut(detail="Winning option not found in this poll."))
    return poll, winning_option, None


@router.post(
    "/events/{event_id}/poll/options/",
    response={201: EventPollOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/h")
def add_poll_option(request, event_id: UUID, payload: PollOptionIn):
    _, poll, err = _get_active_poll(request.auth, event_id)
    if err is not None:
        return err
    next_order = poll.options.count()
    try:
        PollOption.objects.create(poll=poll, datetime=payload.datetime, display_order=next_order)
    except Exception:
        return Status(400, ErrorOut(detail="that time is already an option in this poll"))
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
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/h")
def update_poll_option(request, event_id: UUID, payload: PollOptionIn, option_id: UUID):
    _, poll, err = _get_active_poll(request.auth, event_id)
    if err is not None:
        return err
    try:
        option = poll.options.get(id=option_id)
    except PollOption.DoesNotExist:
        return Status(404, ErrorOut(detail="Option not found."))
    try:
        option.datetime = payload.datetime
        option.save(update_fields=["datetime"])
    except Exception:
        return Status(400, ErrorOut(detail="that time is already an option in this poll"))
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
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/h")
def delete_poll_option(request, event_id: UUID, option_id: UUID):
    _, poll, err = _get_active_poll(request.auth, event_id)
    if err is not None:
        return err
    try:
        option = poll.options.get(id=option_id)
    except PollOption.DoesNotExist:
        return Status(404, ErrorOut(detail="Option not found."))
    if poll.options.count() <= 2:
        return Status(400, ErrorOut(detail="A poll must have at least 2 options."))
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
