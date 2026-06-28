"""Public (no-auth) non-member RSVP submission.

Anonymous visitors RSVP to OFFICIAL, PUBLIC, active, rsvp-enabled events without
an account. A non-member ``User`` row backs each RSVP so the entire existing
RSVP machinery (capacity, plus-ones, waitlist, promotion) is reused unchanged.
A scoped ``NonMemberRsvpToken`` is emailed (never returned in the response) so
the visitor can manage their RSVP at ``/my-rsvps?token=...``.
"""

import logging

from config.audit import audit_log
from config.ratelimit import client_ip, rate_limit
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from notifications._email_helpers import (
    RsvpEmailDetails,
    send_rsvp_confirmation_email,
    send_rsvp_waitlist_promoted_email,
)
from notifications.email_sender import get_email_sender
from pydantic import BaseModel, EmailStr, Field
from users.models import NonMemberRsvpToken, User

from community._event_helpers import _event_out
from community._event_rsvps import _apply_rsvp_in_transaction, _validate_rsvp_status
from community._event_schemas import EventOut
from community._field_limits import FieldLimit
from community._shared import ErrorOut, _validate_phone, logger, validate_display_name
from community._validation import Code, raise_validation
from community.models import Event, EventStatus, EventType, PageVisibility, RSVPStatus

router = Router()


class PublicRsvpIn(BaseModel):
    name: str = Field(max_length=FieldLimit.DISPLAY_NAME)
    email: EmailStr
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    status: str = Field(max_length=FieldLimit.CHOICE)
    has_plus_one: bool = False
    # Honeypot: hidden field humans never fill in. A non-empty value is spam.
    website: str = Field(default="", max_length=FieldLimit.DISPLAY_NAME)


class PublicRsvpStateOut(BaseModel):
    status: str
    has_plus_one: bool


class PublicRsvpOut(BaseModel):
    event: EventOut
    rsvp: PublicRsvpStateOut


def _public_rsvp_decoy(event: Event, status: str, has_plus_one: bool) -> PublicRsvpOut:
    """Mimic a real submission's shape so bots register success and stop retrying.

    No User/RSVP/token row is created and no email is sent. The event payload is
    the anonymous (un-RSVP'd) view, so gated details stay hidden.
    """
    return PublicRsvpOut(
        event=_event_out(event, None),
        rsvp=PublicRsvpStateOut(status=status, has_plus_one=has_plus_one),
    )


def _load_public_rsvp_event(event_id) -> Event:
    """Fetch an event eligible for public RSVP, else 404.

    Every ineligible state collapses to Code.Event.NOT_FOUND so the endpoint
    never leaks the existence of non-public events.
    """
    event = Event.objects.prefetch_related("co_hosts", "invited_users").filter(id=event_id).first()
    if (
        event is None
        or event.event_type != EventType.OFFICIAL
        or event.status != EventStatus.ACTIVE
        or event.visibility != PageVisibility.PUBLIC
        or not event.rsvp_enabled
        or event.is_past
    ):
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    return event


def _reuse_phone_match(phone_match: User, email: str) -> User:
    # Save the submitted email only if blank — never overwrite an existing email
    # (avoids identity churn for a returning non-member).
    if email and not phone_match.email:
        phone_match.email = email
        phone_match.save(update_fields=["email"])
    return phone_match


def _reuse_email_match(email_match: User, phone: str) -> User:
    # Phone is required for non-members; backfill it only if somehow blank.
    if not email_match.phone_number:
        email_match.phone_number = phone
        email_match.save(update_fields=["phone_number"])
    return email_match


def _create_non_member(name: str, email: str, phone: str) -> User:
    # Relies on the unique phone constraint for race safety — a concurrent
    # IntegrityError loser is re-fetched by get_or_create's own SELECT. The
    # email is dropped on a unique-email collision (e.g. an archived row holds
    # it) inside a savepoint so the outer transaction survives; the RSVP still
    # succeeds, just without an email saved on the new row.
    defaults = {"display_name": name, "is_member": False}
    try:
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                phone_number=phone, defaults={**defaults, "email": email or None}
            )
    except IntegrityError:
        user, created = User.objects.get_or_create(phone_number=phone, defaults=defaults)
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def _resolve_both_match(request, phone_match: User, email_match: User) -> User:
    if phone_match.pk == email_match.pk:
        return phone_match  # Same non-member row — reuse, no change.
    # Phone and email point at different non-member rows. Phone is the canonical
    # identifier in this app — reuse it, leave its email as-is, flag for admins.
    audit_log(
        logging.WARNING,
        "public_rsvp_contact_ambiguous",
        request,
        target_type="user",
        target_id=str(phone_match.pk),
        details={"email_user_id": str(email_match.pk)},
    )
    return phone_match


def _resolve_non_member(*, request, name: str, email: str, phone: str) -> User:
    """Resolve (or create) the non-member User backing this RSVP.

    Implements the spec's phone/email collision table. Members → 409. Returns a
    non-member User. Must run inside the surrounding transaction.
    """
    phone_match = User.objects.filter(phone_number=phone, archived_at__isnull=True).first()
    # iexact, not exact: stored emails aren't guaranteed lowercased (the admin
    # members screen stores them verbatim), so an exact match on the normalized
    # input could miss a member and bypass the MEMBER_CONTACT_MUST_SIGN_IN gate.
    email_match = (
        User.objects.filter(email__iexact=email, archived_at__isnull=True).first()
        if email
        else None
    )

    # Either contact belongs to a member → redirect to the authenticated flow.
    if (phone_match and phone_match.is_member) or (email_match and email_match.is_member):
        raise_validation(Code.Event.MEMBER_CONTACT_MUST_SIGN_IN, status_code=409)

    if phone_match and email_match:
        return _resolve_both_match(request, phone_match, email_match)
    if phone_match:
        return _reuse_phone_match(phone_match, email)
    if email_match:
        return _reuse_email_match(email_match, phone)
    return _create_non_member(name, email, phone)


def _format_event_when(event: Event) -> str:
    if event.datetime_tbd or event.start_datetime is None:
        return "to be decided"
    local = timezone.localtime(event.start_datetime)
    return local.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")


def _event_links(event: Event) -> list[str]:
    return [link for link in (event.whatsapp_link, event.partiful_link, event.other_link) if link]


def _email_details(event: Event, user: User, token_str: str) -> RsvpEmailDetails:
    return RsvpEmailDetails(
        to=user.email,
        display_name=user.display_name,
        event_title=event.title,
        event_when=_format_event_when(event),
        event_location=event.location,
        event_links=_event_links(event),
        manage_url=f"{settings.FRONTEND_BASE_URL}/my-rsvps?token={token_str}",
    )


def _log_email_failure(request, event: Event, user: User, exc: Exception) -> None:
    logger.warning("public rsvp email failed", exc_info=True)
    audit_log(
        logging.WARNING,
        "public_rsvp_email_failed",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"user_id": str(user.pk), "error": str(exc)},
    )


def _send_confirmation_email(
    request, event: Event, user: User, token_str: str, waitlisted: bool
) -> None:
    """Best-effort confirmation email. A send failure must NOT roll back the RSVP."""
    if not user.email:
        return
    try:
        result = send_rsvp_confirmation_email(
            sender=get_email_sender(),
            details=_email_details(event, user, token_str),
            waitlisted=waitlisted,
        )
        if not result.success:
            raise RuntimeError(result.error or "send returned failure")
    except Exception as exc:
        _log_email_failure(request, event, user, exc)


def _email_promoted_non_members(request, event: Event, promoted_user_ids: list[str]) -> None:
    """Email any promoted non-members a fresh manage link. Best-effort per user."""
    if not promoted_user_ids:
        return
    promoted = User.objects.filter(id__in=promoted_user_ids, is_member=False, email__isnull=False)
    for user in promoted:
        if not user.email:
            continue
        try:
            token = NonMemberRsvpToken.issue(user)
            result = send_rsvp_waitlist_promoted_email(
                sender=get_email_sender(),
                details=_email_details(event, user, token.token),
            )
            if not result.success:
                raise RuntimeError(result.error or "send returned failure")
        except Exception as exc:
            _log_email_failure(request, event, user, exc)


@router.post(
    "/public/events/{event_id}/rsvp/",
    response={200: PublicRsvpOut, 400: ErrorOut, 404: ErrorOut, 409: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="5/h")
def submit_public_rsvp(request, event_id, payload: PublicRsvpIn):
    event = _load_public_rsvp_event(event_id)

    # Honeypot trip — decoy 200 without persisting. Checked before field
    # validation so a bot gets no validation feedback to iterate against.
    if payload.website.strip():
        audit_log(
            logging.WARNING,
            "public_rsvp_honeypot_tripped",
            request,
            target_type="event",
            target_id=str(event_id),
        )
        return Status(200, _public_rsvp_decoy(event, payload.status, payload.has_plus_one))

    name = payload.name.strip()
    validate_display_name(name, field="name")
    validated_phone = _validate_phone(payload.phone_number)
    normalized_email = payload.email.strip().lower()
    _validate_rsvp_status(payload.status)

    with transaction.atomic():
        user = _resolve_non_member(
            request=request, name=name, email=normalized_email, phone=validated_phone
        )
        final_status, promoted_user_ids = _apply_rsvp_in_transaction(
            event.id, user, payload.status, payload.has_plus_one
        )
        token = NonMemberRsvpToken.issue(user)

    audit_log(
        logging.INFO,
        "public_rsvp_created",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"user_id": str(user.pk), "status": final_status},
    )

    waitlisted = final_status == RSVPStatus.WAITLISTED
    _send_confirmation_email(request, event, user, token.token, waitlisted)
    _email_promoted_non_members(request, event, promoted_user_ids)

    fresh_event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .get(id=event.id)
    )
    final_rsvp = user.event_rsvps.get(event=fresh_event)
    return Status(
        200,
        PublicRsvpOut(
            event=_event_out(fresh_event, user),
            rsvp=PublicRsvpStateOut(status=final_rsvp.status, has_plus_one=final_rsvp.has_plus_one),
        ),
    )
