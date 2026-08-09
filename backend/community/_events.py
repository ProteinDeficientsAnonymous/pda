"""Events CRUD endpoints."""

import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from config.media_proxy import media_path
from config.ratelimit import rate_limit
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from notifications.service import broadcast_event_created
from users._helpers import visible_display_name

from community._cohost_invite_helpers import has_pending_cohost_invite
from community._event_helpers import (
    _can_edit_event,
    _can_see_invite_only,
    _enforce_type_tag_permission,
    _event_out,
    _get_creator_name,
    _is_invalid_typed_visibility,
    _my_rsvp_fields,
    _set_event_tags,
    _tags_out,
    broadcast_capacity_change,
)
from community._event_nonmember_removal import (
    email_removed_non_members,
    guard_or_remove_ineligible_non_members,
)
from community._event_schemas import (
    EventIn,
    EventListOut,
    EventOut,
    EventPatchIn,
    validate_event_rsvp_question,
)
from community._event_transitions import _handle_status_update, _set_event_participants
from community._event_update import (
    _apply_field_updates,
    _guard_can_edit_event,
    _promote_if_capacity_increased,
)
from community._event_viewer import resolve_event_viewer
from community._public_rsvp_shared import _email_promoted_non_members
from community._rsvp_counts import _attending_headcount, _waitlisted_count
from community._rsvp_payment import can_see_payment_details
from community._shared import ErrorOut, _authenticated_user, _gated, _optional_jwt
from community._validation import Code, raise_validation
from community.models import (
    Event,
    EventRsvpQuestion,
    EventStatus,
    PageVisibility,
    parse_event_ref,
)

router = Router()


def _validate_event_datetimes(start, end, datetime_tbd: bool, *, check_past: bool = True) -> None:
    """Raise ValidationException if datetime fields are invalid."""
    if start is None:
        if not datetime_tbd:
            raise_validation(Code.Event.START_DATETIME_REQUIRED_UNLESS_TBD, field="start_datetime")
        return
    if end is not None and end <= start:
        raise_validation(Code.Event.END_BEFORE_START, field="end_datetime")
    if check_past and not datetime_tbd and start < timezone.now():
        raise_validation(Code.Event.START_DATETIME_MUST_BE_FUTURE, field="start_datetime")


def _build_events_queryset(status: str, auth_user, is_authed):
    """Build the events queryset for list_events based on status and auth state."""
    if status in (EventStatus.CANCELLED, EventStatus.DRAFT):
        return (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users", "rsvps", "poll", "tags")
            .annotate(
                comment_count=Count(
                    "comments",
                    filter=Q(comments__deleted_at__isnull=True),
                    distinct=True,
                )
            )
            .filter(status=status)
            .filter(Q(created_by=auth_user) | Q(co_hosts=auth_user))
            .distinct()
        )
    qs = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps", "poll", "tags")
        .annotate(
            comment_count=Count(
                "comments",
                filter=Q(comments__deleted_at__isnull=True),
                distinct=True,
            )
        )
        .filter(status=EventStatus.ACTIVE)
    )
    if not is_authed:
        qs = qs.filter(visibility=PageVisibility.PUBLIC)
    return qs


def _filter_invite_only(events, auth_user, status: str):
    """Remove invite-only events the user cannot see (skip for cancelled/draft status queries)."""
    if not auth_user or status in (EventStatus.CANCELLED, EventStatus.DRAFT):
        return events
    return [
        e
        for e in events
        if e.visibility != PageVisibility.INVITE_ONLY
        or _can_see_invite_only(
            auth_user,
            {str(c.id) for c in e.co_hosts.all()},
            {str(u.id) for u in e.invited_users.all()},
            e.created_by_id,
        )
    ]


def _event_list_out(e, auth_user, is_authed: bool) -> EventListOut:
    show_payment_details = can_see_payment_details(e, is_authed)
    my_rsvp_status, my_paid_confirmed = _my_rsvp_fields(e.rsvps.all(), auth_user)
    return EventListOut(
        id=str(e.id),
        slug=e.slug,
        title=e.title,
        description=e.description,
        start_datetime=e.start_datetime,
        end_datetime=e.end_datetime,
        location=e.location,
        latitude=float(e.latitude) if e.latitude is not None else None,
        longitude=float(e.longitude) if e.longitude is not None else None,
        event_type=e.event_type,
        visibility=e.visibility,
        photo_url=media_path(e.photo),
        photo_updated_at=(e.photo_updated_at.isoformat() if e.photo_updated_at else None),
        whatsapp_link=_gated(e.whatsapp_link, "", is_authed),
        partiful_link=_gated(e.partiful_link, "", is_authed),
        other_link=_gated(e.other_link, "", is_authed),
        price=e.price,
        venmo_link=_gated(e.venmo_link, "", show_payment_details),
        cashapp_link=_gated(e.cashapp_link, "", show_payment_details),
        zelle_info=_gated(e.zelle_info, "", show_payment_details),
        created_by_id=str(e.created_by_id) if e.created_by_id else None,
        created_by_name=_get_creator_name(e.created_by, auth_user),
        created_by_photo_url=media_path(e.created_by.profile_photo) if e.created_by else "",
        co_host_photo_urls=[media_path(c.profile_photo) for c in e.co_hosts.all()],
        datetime_tbd=e.datetime_tbd,
        has_poll=hasattr(e, "poll"),
        allow_plus_ones=e.allow_plus_ones,
        max_attendees=e.max_attendees,
        attending_count=_attending_headcount(e),
        waitlisted_count=_waitlisted_count(e),
        invited_count=e.invited_users.count(),
        comment_count=e.comment_count,
        my_rsvp=my_rsvp_status,
        my_paid_confirmed=my_paid_confirmed,
        co_host_ids=[str(c.id) for c in e.co_hosts.all()],
        co_host_names=[visible_display_name(c, auth_user) for c in e.co_hosts.all()],
        is_past=e.is_past,
        status=e.status,
        tags=_tags_out(e),
    )


@router.get("/events/", response={200: list[EventListOut], 403: ErrorOut}, auth=_optional_jwt)
def list_events(request, status: str = EventStatus.ACTIVE):
    auth_user = _authenticated_user(request.auth)
    is_authed = auth_user is not None

    if status in (EventStatus.CANCELLED, EventStatus.DRAFT) and not is_authed:
        raise_validation(Code.Event.AUTH_REQUIRED, status_code=403)

    events = _filter_invite_only(
        list(_build_events_queryset(status, auth_user, is_authed)), auth_user, status
    )
    return Status(
        200,
        [_event_list_out(e, auth_user, is_authed) for e in events],
    )


def _can_see_draft(event: Event, auth_user) -> bool:
    """Pending cohost invitees can see the draft they were invited to so they
    can find the accept/decline banner. They aren't accepted co-hosts yet,
    so `_can_edit_event` returns False — without this branch, they'd 404."""
    if not auth_user:
        return False
    return _can_edit_event(auth_user, event) or has_pending_cohost_invite(event, auth_user)


def _enforce_event_read_visibility(event: Event, auth_user) -> None:
    """Raise the right ValidationException if `auth_user` shouldn't see this event."""
    if event.is_deleted:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if event.is_draft and not _can_see_draft(event, auth_user):
        raise_validation(Code.Event.PERM_DENIED, status_code=403, action="view_draft_event")
    if event.visibility == PageVisibility.MEMBERS_ONLY and auth_user is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if event.visibility == PageVisibility.INVITE_ONLY:
        co_host_ids = {str(c.id) for c in event.co_hosts.all()}
        invited_user_ids = {str(u.id) for u in event.invited_users.all()}
        if not _can_see_invite_only(auth_user, co_host_ids, invited_user_ids, event.created_by_id):
            raise_validation(
                Code.Event.PERM_DENIED, status_code=403, action="view_invite_only_event"
            )


@router.get(
    "/events/{event_id}/",
    response={200: EventOut, 403: ErrorOut, 404: ErrorOut},
    auth=_optional_jwt,
)
def get_event(request, event_id: str):
    ref = parse_event_ref(event_id)
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users", "rsvps__user", "tags", "rsvp_questions")
            .annotate(
                comment_count=Count(
                    "comments",
                    filter=Q(comments__deleted_at__isnull=True),
                    distinct=True,
                )
            )
            .get(ref.as_q())
        )
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    viewer = resolve_event_viewer(request, event.id)
    _enforce_event_read_visibility(event, viewer)
    return Status(200, _event_out(event, viewer))


@router.post(
    "/events/",
    response={201: EventOut, 400: ErrorOut, 403: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/d")
def create_event(request, payload: EventIn):
    # Any authenticated member can create community or draft events.
    # Official/club events require their respective tag permission.
    # Subsequent draft saves use PATCH (no rate limit hit).
    if payload.status not in (EventStatus.ACTIVE, EventStatus.DRAFT):
        raise_validation(Code.Event.INVALID_CREATE_STATUS, field="status", status_code=400)

    _enforce_type_tag_permission(request, payload.event_type, "create_event")

    if _is_invalid_typed_visibility(payload.event_type, payload.visibility):
        raise_validation(Code.Event.OFFICIAL_MUST_BE_PUBLIC, status_code=400)

    # Drafts can save without a start_datetime (see #357). But if a start IS
    # provided, the same rules apply as for any event — must be in the future,
    # end must be after start.
    if not (payload.status == EventStatus.DRAFT and payload.start_datetime is None):
        _validate_event_datetimes(
            payload.start_datetime,
            payload.end_datetime,
            payload.datetime_tbd,
            check_past=True,
        )

    for question in payload.rsvp_questions:
        validate_event_rsvp_question(question)

    event = Event.objects.create(
        title=payload.title,
        description=payload.description,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        location=payload.location,
        latitude=payload.latitude,
        longitude=payload.longitude,
        whatsapp_link=payload.whatsapp_link,
        partiful_link=payload.partiful_link,
        other_link=payload.other_link,
        price=payload.price,
        venmo_link=payload.venmo_link,
        cashapp_link=payload.cashapp_link,
        zelle_info=payload.zelle_info,
        rsvp_enabled=payload.rsvp_enabled,
        datetime_tbd=payload.datetime_tbd,
        allow_plus_ones=payload.allow_plus_ones,
        max_attendees=payload.max_attendees,
        event_type=payload.event_type,
        visibility=payload.visibility,
        invite_permission=payload.invite_permission,
        status=payload.status,
        created_by=request.auth,
    )
    _set_event_participants(request, event, payload.co_host_ids)
    _set_event_tags(event, payload.tag_ids)
    EventRsvpQuestion.objects.bulk_create(
        [
            EventRsvpQuestion(
                event=event,
                label=question.label,
                field_type=question.field_type,
                options=question.options,
                required=question.required,
                display_order=display_order,
            )
            for display_order, question in enumerate(payload.rsvp_questions)
        ]
    )
    if event.status == EventStatus.ACTIVE:
        transaction.on_commit(lambda: broadcast_event_created(event))
    audit_log(
        logging.INFO,
        "event_created_draft" if event.is_draft else "event_created",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT,
            id=str(event.id),
            details={
                "title": event.title,
                "event_type": event.event_type,
                "visibility": event.visibility,
                "status": event.status,
            },
        ),
    )
    return Status(201, _event_out(event, request.auth))


@router.patch(
    "/events/{event_id}/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 409: ErrorOut},
    auth=gated_jwt,
)
def update_event(request, event_id: UUID, payload: EventPatchIn):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users", "rsvps__user", "tags", "rsvp_questions")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)

    if event.is_deleted:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)

    _guard_can_edit_event(request, event, event_id)

    updates = payload.model_dump(exclude_unset=True)
    new_status = updates.pop("status", None)
    notify_attendees = updates.pop("notify_attendees", False) or False
    force = updates.pop("force", False) or False
    # Checked before status transitions, which have their own attendee notifications.
    was_eligible = event.is_public_rsvp_eligible
    old_max_attendees = event.max_attendees
    removed_user_ids: list[str] = []
    promoted_user_ids: list[str] = []

    # Field edits before the transition so publish validates the corrected date.
    with transaction.atomic():
        _apply_field_updates(request, event, event_id, updates)

        if was_eligible and not event.is_public_rsvp_eligible:
            removed_user_ids = guard_or_remove_ineligible_non_members(event, force)

        if new_status is not None:
            early = _handle_status_update(request, event, new_status, notify_attendees)
            if early is not None:
                return early

        promoted_user_ids = _promote_if_capacity_increased(event, updates, old_max_attendees)

    email_removed_non_members(request, event, removed_user_ids)
    if promoted_user_ids:
        broadcast_capacity_change(event_id, exclude_user_ids={str(request.auth.pk)})
        _email_promoted_non_members(request, event, promoted_user_ids)

    # Re-fetch to pick up any M2M changes
    event.refresh_from_db()
    return Status(200, _event_out(event, request.auth))
