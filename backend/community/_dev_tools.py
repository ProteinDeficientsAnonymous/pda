import logging
import os
from datetime import timedelta

from config.audit import audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._dev_tools_content import generate_placeholder_photo, random_event_title
from community._dev_tools_populate import (
    RsvpCounts,
    populate_cohosts,
    populate_invited_users,
    populate_rsvps,
)
from community._event_helpers import _event_out
from community._event_schemas import EventOut
from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.management.commands._seed_staging_data import is_seed_allowed
from community.models import Event, EventRSVP, EventStatus, EventType, PageVisibility, RSVPStatus

router = Router()

MAX_PARTICIPANTS = 50


class DevTestEventIn(BaseModel):
    is_past: bool = False
    is_canceled: bool = False
    is_official: bool = False
    is_club: bool = False
    make_me_host: bool = False
    make_me_guest: bool = False
    price: str = Field(default="", max_length=FieldLimit.SHORT_TEXT)
    venmo_link: str = Field(default="", max_length=FieldLimit.PAYMENT_HANDLE)
    cashapp_link: str = Field(default="", max_length=FieldLimit.PAYMENT_HANDLE)
    zelle_info: str = Field(default="", max_length=FieldLimit.SHORT_TEXT)
    cohost_count: int = Field(default=5, ge=0, le=MAX_PARTICIPANTS)
    invited_cohost_count: int = Field(default=5, ge=0, le=MAX_PARTICIPANTS)
    going_count: int = Field(default=5, ge=0, le=MAX_PARTICIPANTS)
    non_member_going_count: int = Field(default=0, ge=0, le=MAX_PARTICIPANTS)
    maybe_count: int = Field(default=5, ge=0, le=MAX_PARTICIPANTS)
    cant_go_count: int = Field(default=5, ge=0, le=MAX_PARTICIPANTS)
    invited_count: int = Field(default=5, ge=0, le=MAX_PARTICIPANTS)
    rsvp_enabled: bool = True
    visibility: str = Field(default=PageVisibility.PUBLIC, max_length=FieldLimit.CHOICE)
    max_attendees: int | None = Field(default=None, ge=1)
    allow_plus_ones: bool = False


def _dev_tools_allowed() -> bool:
    return is_seed_allowed(os.environ.get("RAILWAY_ENVIRONMENT_NAME"), force=False)


def _require_dev_tools(request) -> None:
    if not _dev_tools_allowed():
        raise_validation(Code.DevTools.NOT_FOUND, status_code=404)
    if not request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        raise_validation(Code.DevTools.NOT_FOUND, status_code=404)


def _event_datetimes(payload: DevTestEventIn) -> tuple:
    now = timezone.now()
    if payload.is_past:
        start = now - timedelta(days=7)
    else:
        start = now + timedelta(days=7)
    return start, start + timedelta(hours=2)


def _event_type(payload: DevTestEventIn) -> str:
    if payload.is_official:
        return EventType.OFFICIAL
    if payload.is_club:
        return EventType.CLUB
    return EventType.COMMUNITY


@router.post(
    "/dev/test-events/",
    response={201: EventOut, 404: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/h")
def create_dev_test_event(request, payload: DevTestEventIn):
    _require_dev_tools(request)

    start, end = _event_datetimes(payload)
    status = EventStatus.CANCELLED if payload.is_canceled else EventStatus.ACTIVE
    event_type = _event_type(payload)
    # Mirrors _is_invalid_typed_visibility, which this dev endpoint bypasses.
    is_public_only_type = event_type in (EventType.OFFICIAL, EventType.CLUB)
    visibility = PageVisibility.PUBLIC if is_public_only_type else payload.visibility
    # Mirrors Event.is_public_rsvp_eligible.
    non_member_going_count = (
        payload.non_member_going_count
        if (payload.is_official and status == EventStatus.ACTIVE and payload.rsvp_enabled)
        else 0
    )

    event = Event.objects.create(
        title=random_event_title(),
        description="created by the dev test-events tool",
        start_datetime=start,
        end_datetime=end,
        event_type=event_type,
        visibility=visibility,
        rsvp_enabled=payload.rsvp_enabled,
        max_attendees=payload.max_attendees,
        allow_plus_ones=payload.allow_plus_ones,
        status=status,
        price=payload.price,
        venmo_link=payload.venmo_link,
        cashapp_link=payload.cashapp_link,
        zelle_info=payload.zelle_info,
        created_by=request.auth,
    )
    event.photo.save(f"{event.id}.jpg", generate_placeholder_photo(), save=False)
    event.photo_updated_at = timezone.now()
    event.save(update_fields=["photo", "photo_updated_at"])

    # Undo seed_creator_as_host's auto-add unless the caller opted in.
    if not payload.make_me_host:
        event.co_hosts.remove(request.auth)

    populate_cohosts(
        event,
        accepted_count=payload.cohost_count,
        invited_count=payload.invited_cohost_count,
        invited_by=request.auth,
    )
    populate_rsvps(
        event,
        RsvpCounts(
            going=payload.going_count,
            non_member_going=non_member_going_count,
            maybe=payload.maybe_count,
            cant_go=payload.cant_go_count,
            max_attendees=payload.max_attendees,
        ),
    )
    populate_invited_users(event, count=payload.invited_count)

    if payload.make_me_guest:
        EventRSVP.objects.update_or_create(
            event=event, user=request.auth, defaults={"status": RSVPStatus.ATTENDING}
        )

    audit_log(
        logging.INFO,
        "dev_test_event_created",
        request,
        target_type="event",
        target_id=str(event.id),
    )
    return Status(201, _event_out(event, request.auth))
