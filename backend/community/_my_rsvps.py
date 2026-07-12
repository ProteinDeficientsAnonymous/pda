import logging

from config.audit import audit_log
from config.ratelimit import client_ip, rate_limit
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel
from users.models import NonMemberRsvpToken, User

from community._event_helpers import _event_out, promote_from_waitlist
from community._event_rsvps import _apply_rsvp_in_transaction, _validate_rsvp_status
from community._event_schemas import EventOut
from community._public_rsvp_shared import (
    PublicRsvpOut,
    PublicRsvpStateOut,
    _email_promoted_non_members,
    _load_public_rsvp_event,
)
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import (
    Event,
    EventRSVP,
    EventStatus,
    EventType,
    PageVisibility,
    RSVPStatus,
)

router = Router()


class MyRsvpsUserOut(BaseModel):
    display_name: str
    email: str
    phone_number: str


class MyRsvpItemOut(BaseModel):
    event: EventOut
    status: str
    has_plus_one: bool


class MyRsvpsOut(BaseModel):
    user: MyRsvpsUserOut
    rsvps: list[MyRsvpItemOut]


class ManageRsvpIn(BaseModel):
    status: str
    has_plus_one: bool = False


def _resolve_token_user(token: str) -> User:
    """Resolve a manage-rsvp token to its non-member user, or 404."""
    user = NonMemberRsvpToken.resolve_user(token)
    if user is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    return user


def _eligible_event_rsvps(user):
    """The user's RSVPs on events still public-RSVP-eligible, matching _load_public_rsvp_event."""
    # Ineligible events must drop out, else their member-only details leak to the token holder.
    now = timezone.now()
    past = Q(event__datetime_tbd=False) & (
        Q(event__end_datetime__lt=now)
        | Q(event__end_datetime__isnull=True, event__start_datetime__lt=now)
    )
    return (
        user.event_rsvps.filter(
            event__event_type=EventType.OFFICIAL,
            event__status=EventStatus.ACTIVE,
            event__visibility=PageVisibility.PUBLIC,
            event__rsvp_enabled=True,
        )
        .exclude(past)
        .annotate(
            event_comment_count=Count(
                "event__comments",
                filter=Q(event__comments__deleted_at__isnull=True),
                distinct=True,
            )
        )
        .select_related("event", "event__created_by")
        .prefetch_related("event__co_hosts", "event__invited_users", "event__rsvps__user")
    )


@router.get(
    "/public/my-rsvps/",
    response={200: MyRsvpsOut, 404: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="30/h")
def list_my_rsvps(request, token: str = ""):
    user = _resolve_token_user(token)
    items = []
    for rsvp in _eligible_event_rsvps(user):
        # Feed the annotation to _event_out's event.comment_count lookup, avoiding a per-event query.
        rsvp.event.comment_count = rsvp.event_comment_count
        items.append(
            MyRsvpItemOut(
                event=_event_out(rsvp.event, user),
                status=rsvp.status,
                has_plus_one=rsvp.has_plus_one,
            )
        )
    return 200, MyRsvpsOut(
        user=MyRsvpsUserOut(
            display_name=user.display_name,
            email=user.email or "",
            phone_number=user.phone_number,
        ),
        rsvps=items,
    )


@router.post(
    "/public/my-rsvps/{event_id}/",
    response={200: PublicRsvpOut, 400: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="30/h")
def update_my_rsvp(request, event_id, payload: ManageRsvpIn, token: str = ""):
    user = _resolve_token_user(token)
    event = _load_public_rsvp_event(event_id)
    _validate_rsvp_status(payload.status)

    with transaction.atomic():
        final_status, promoted_user_ids = _apply_rsvp_in_transaction(
            event.id, user, payload.status, payload.has_plus_one
        )
        NonMemberRsvpToken.issue_or_extend(user)

    audit_log(
        logging.INFO,
        "public_rsvp_updated",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"user_id": str(user.pk), "status": final_status},
    )
    _email_promoted_non_members(request, event, promoted_user_ids)

    fresh_event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .get(id=event.id)
    )
    final_rsvp = user.event_rsvps.get(event=fresh_event)
    return 200, PublicRsvpOut(
        event=_event_out(fresh_event, user),
        rsvp=PublicRsvpStateOut(status=final_rsvp.status, has_plus_one=final_rsvp.has_plus_one),
    )


@router.delete(
    "/public/my-rsvps/{event_id}/",
    response={204: None, 404: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="30/h")
def delete_my_rsvp(request, event_id, token: str = ""):
    user = _resolve_token_user(token)
    with transaction.atomic():
        event = (
            Event.objects.select_for_update()
            .prefetch_related("co_hosts", "invited_users")
            .filter(id=event_id)
            .first()
        )
        if event is None:
            raise_validation(Code.Event.NOT_FOUND, status_code=404)
        rsvp = EventRSVP.objects.filter(event=event, user=user).first()
        if not rsvp:
            raise_validation(Code.Event.RSVP_NOT_FOUND, status_code=404)
        was_attending = rsvp.status == RSVPStatus.ATTENDING
        rsvp.delete()
        if was_attending:
            promote_from_waitlist(event)

    audit_log(
        logging.INFO,
        "public_rsvp_deleted",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"user_id": str(user.pk)},
    )
    return Status(204, None)
