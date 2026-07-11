import logging

from config.audit import audit_log
from config.ratelimit import client_ip, rate_limit
from django.db import transaction
from ninja import Router
from pydantic import BaseModel
from users.models import NonMemberRsvpToken, User

from community._event_helpers import _event_out
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
from community.models import Event, EventType

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


@router.get(
    "/public/my-rsvps/",
    response={200: MyRsvpsOut, 404: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="30/h")
def list_my_rsvps(request, token: str = ""):
    user = _resolve_token_user(token)
    rsvps = (
        user.event_rsvps.filter(event__event_type=EventType.OFFICIAL)
        .select_related("event", "event__created_by")
        .prefetch_related("event__co_hosts", "event__invited_users", "event__rsvps__user")
    )
    items = [
        MyRsvpItemOut(
            event=_event_out(rsvp.event, user),
            status=rsvp.status,
            has_plus_one=rsvp.has_plus_one,
        )
        for rsvp in rsvps
    ]
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
