import logging

from config.audit import audit_log
from config.ratelimit import client_ip, rate_limit
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from notifications._email_helpers import send_rsvp_updated_email
from notifications.email_sender import get_email_sender
from pydantic import BaseModel, Field
from users.models import NonMemberRsvpToken, User

from community._event_helpers import _event_out, broadcast_capacity_change, promote_from_waitlist
from community._event_rsvps import (
    _apply_rsvp_in_transaction,
    _post_rsvp_comment,
    _validate_rsvp_status,
)
from community._event_schemas import EventOut
from community._field_limits import FieldLimit
from community._public_rsvp_shared import (
    PublicRsvpOut,
    PublicRsvpStateOut,
    _email_details,
    _email_promoted_non_members,
    _load_public_rsvp_event,
    _log_email_failure,
)
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event, EventRSVP, RSVPStatus
from community.models.event import public_rsvp_eligible_q

router = Router()


class PublicRsvpManageUserOut(BaseModel):
    display_name: str
    email: str
    phone_number: str


class PublicRsvpManageItemOut(BaseModel):
    event: EventOut
    status: str
    has_plus_one: bool


class PublicRsvpManageOut(BaseModel):
    user: PublicRsvpManageUserOut
    rsvps: list[PublicRsvpManageItemOut]


class PublicRsvpManageIn(BaseModel):
    status: str
    has_plus_one: bool = False
    comment: str | None = Field(default=None, max_length=FieldLimit.SHORT_TEXT)


def _resolve_token_user(token: str) -> User:
    """Resolve a manage-rsvp token to its non-member user, or 404."""
    user = NonMemberRsvpToken.resolve_user(token)
    if user is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    return user


def _eligible_event_rsvps(user):
    """The user's RSVPs on events still public-RSVP-eligible, matching _load_public_rsvp_event."""
    # Ineligible events must drop out, else their member-only details leak to the token holder.
    return (
        user.event_rsvps.filter(public_rsvp_eligible_q(timezone.now(), prefix="event__"))
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


def _send_updated_email(request, event: Event, user: User, token_str: str) -> None:
    """Best-effort "rsvp updated" email. A send failure must NOT roll back the RSVP."""
    if not user.email:
        return
    try:
        result = send_rsvp_updated_email(
            sender=get_email_sender(),
            details=_email_details(event, user, token_str),
        )
        if not result.success:
            raise RuntimeError(result.error or "send returned failure")
    except Exception as exc:
        _log_email_failure(request, event, user, exc)


@router.get(
    "/public/my-rsvps/",
    response={200: PublicRsvpManageOut, 404: ErrorOut, 429: ErrorOut},
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
            PublicRsvpManageItemOut(
                event=_event_out(rsvp.event, user),
                status=rsvp.status,
                has_plus_one=rsvp.has_plus_one,
            )
        )
    return 200, PublicRsvpManageOut(
        user=PublicRsvpManageUserOut(
            display_name=user.full_name,
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
def update_my_rsvp(request, event_id, payload: PublicRsvpManageIn, token: str = ""):
    user = _resolve_token_user(token)
    event = _load_public_rsvp_event(event_id)
    _validate_rsvp_status(payload.status)

    with transaction.atomic():
        final_status, promoted_user_ids = _apply_rsvp_in_transaction(
            event.id, user, payload.status, payload.has_plus_one
        )
        rsvp_token = NonMemberRsvpToken.issue_or_extend(user)

    audit_log(
        logging.INFO,
        "public_rsvp_updated",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"user_id": str(user.pk), "status": final_status},
    )
    _post_rsvp_comment(event.id, user, final_status, payload.comment)
    _send_updated_email(request, event, user, rsvp_token.token)
    _email_promoted_non_members(request, event, promoted_user_ids)
    broadcast_capacity_change(event.id)

    fresh_event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .get(id=event.id)
    )
    final_rsvp = user.event_rsvps.get(event=fresh_event)
    return 200, PublicRsvpOut(
        event=_event_out(fresh_event, user),
        rsvp=PublicRsvpStateOut(status=final_rsvp.status, has_plus_one=final_rsvp.has_plus_one),
        rsvp_token=rsvp_token.token,
    )


@router.delete(
    "/public/my-rsvps/{event_id}/",
    response={204: None, 404: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="30/h")
def delete_my_rsvp(request, event_id, token: str = ""):
    user = _resolve_token_user(token)
    promoted_user_ids: list[str] = []
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
            promoted_user_ids = promote_from_waitlist(event)

    audit_log(
        logging.INFO,
        "public_rsvp_deleted",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"user_id": str(user.pk)},
    )
    _email_promoted_non_members(request, event, promoted_user_ids)
    broadcast_capacity_change(event.id)
    return Status(204, None)
