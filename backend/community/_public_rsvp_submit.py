import logging
from enum import StrEnum

from config.audit import audit_log
from config.ratelimit import client_ip, rate_limit
from django.conf import settings
from django.db import IntegrityError, transaction
from ninja import Router
from ninja.responses import Status
from notifications._email_helpers import send_rsvp_confirmation_email, send_rsvp_manage_link_email
from notifications.email_sender import get_email_sender
from pydantic import BaseModel, EmailStr, Field
from users.models import PUBLIC_FORM_PHONE_REGION, NonMemberRsvpToken, User, validate_phone

from community._event_helpers import _event_out, broadcast_capacity_change
from community._event_rsvps import (
    _apply_rsvp_in_transaction,
    _post_rsvp_comment,
    _validate_rsvp_status,
)
from community._field_limits import FieldLimit
from community._public_rsvp_shared import (
    PublicRsvpOut,
    PublicRsvpStateOut,
    _email_details,
    _email_promoted_non_members,
    _load_public_rsvp_event,
    _log_email_failure,
)
from community._shared import ErrorOut, validate_display_name
from community._validation import Code, ValidationException, raise_validation
from community.models import Event, RSVPStatus

router = Router()


class PublicRsvpIn(BaseModel):
    first_name: str = Field(max_length=FieldLimit.FIRST_NAME)
    last_name: str = Field(default="", max_length=FieldLimit.LAST_NAME)
    email: EmailStr
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    status: str = Field(max_length=FieldLimit.CHOICE)
    has_plus_one: bool = False
    comment: str | None = Field(default=None, max_length=FieldLimit.SHORT_TEXT)
    # Honeypot: hidden field humans never fill in. A non-empty value is spam.
    website: str = Field(default="", max_length=FieldLimit.DISPLAY_NAME)


class PublicRsvpPhoneStatus(StrEnum):
    EXISTING = "existing"
    NEW = "new"


class PublicRsvpPhoneCheckIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)


class PublicRsvpPhoneCheckOut(BaseModel):
    status: PublicRsvpPhoneStatus


def _public_rsvp_decoy(event: Event, status: str, has_plus_one: bool) -> PublicRsvpOut:
    """Mimic a real submission's shape (no rows created, no email) so bots register success."""
    return PublicRsvpOut(
        event=_event_out(event, None),
        rsvp=PublicRsvpStateOut(status=status, has_plus_one=has_plus_one),
        rsvp_token="",
    )


def _backfill_email(phone_match: User, email: str) -> User:
    # Backfill the email only if blank — never overwrite an existing one.
    if email and not phone_match.email:
        phone_match.email = email
        phone_match.save(update_fields=["email"])
    return phone_match


def _create_non_member(first_name: str, last_name: str, email: str, phone: str) -> User:
    """Get-or-create the non-member User keyed on the unique phone number.

    A unique-email collision (e.g. an archived user still holding that email)
    raises email.already_exists rather than silently dropping the email.
    """
    defaults = {"first_name": first_name, "last_name": last_name, "is_member": False}
    try:
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                phone_number=phone, defaults={**defaults, "email": email or None}
            )
    except IntegrityError:
        raise_validation(Code.Email.ALREADY_EXISTS, field="email", status_code=409)
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def _resolve_both_match(request, phone_match: User, email_match: User) -> User:
    # Same row → the phone and email belong to one user; reuse it.
    if phone_match.pk == email_match.pk:
        return phone_match
    # Different rows: phone is canonical — reuse it and flag the ambiguity for admins.
    audit_log(
        logging.WARNING,
        "public_rsvp_contact_ambiguous",
        request,
        target_type="user",
        target_id=str(phone_match.pk),
        details={"email_user_id": str(email_match.pk)},
    )
    return phone_match


def _resolve_non_member(
    *, request, first_name: str, last_name: str, email: str, phone: str
) -> User:
    """Resolve (or create) the non-member User backing this RSVP; member contact → 409.

    Must run inside the surrounding transaction.
    """
    phone_match = User.objects.filter(phone_number=phone, archived_at__isnull=True).first()
    # iexact so a mixed-case stored member email (e.g. admin-created) still trips
    # the member gate below — the incoming email is already lowercased.
    email_match = (
        User.objects.filter(email__iexact=email, archived_at__isnull=True).first()
        if email
        else None
    )

    if (phone_match and phone_match.is_member) or (email_match and email_match.is_member):
        raise_validation(Code.Event.MEMBER_CONTACT_MUST_SIGN_IN, status_code=409)

    if phone_match and email_match:
        return _resolve_both_match(request, phone_match, email_match)
    if phone_match:
        return _backfill_email(phone_match, email)
    if email_match:
        return email_match
    return _create_non_member(first_name, last_name, email, phone)


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


def _send_recognized_login_link(request, user: User) -> None:
    """Email a returning non-member their manage link instead of re-asking for contact info.

    Best-effort — a send failure must not block the phone-check response.
    """
    token = NonMemberRsvpToken.issue_or_extend(user)
    manage_url = f"{settings.FRONTEND_BASE_URL}/my-rsvps?token={token.token}"
    try:
        result = send_rsvp_manage_link_email(
            sender=get_email_sender(),
            to=user.email,
            display_name=user.full_name,
            manage_url=manage_url,
        )
        if not result.success:
            raise RuntimeError(result.error or "send returned failure")
    except Exception as exc:
        audit_log(
            logging.WARNING,
            "public_rsvp_recognized_email_failed",
            request,
            target_type="user",
            target_id=str(user.pk),
            details={"error": str(exc)},
        )


@router.post(
    "/public/events/{event_id}/rsvp-phone-check/",
    response={200: PublicRsvpPhoneCheckOut, 404: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="20/h")
def check_public_rsvp_phone(request, event_id, payload: PublicRsvpPhoneCheckIn):
    """Collapses member/already-rsvpd/recognized into EXISTING so an anonymous caller can't enumerate membership or attendance by phone number."""
    event = _load_public_rsvp_event(event_id)
    try:
        phone = validate_phone(payload.phone_number, PUBLIC_FORM_PHONE_REGION)
    except ValidationException:
        return Status(200, PublicRsvpPhoneCheckOut(status=PublicRsvpPhoneStatus.NEW))

    user = User.objects.filter(phone_number=phone, archived_at__isnull=True).first()
    if user is None:
        return Status(200, PublicRsvpPhoneCheckOut(status=PublicRsvpPhoneStatus.NEW))
    if user.is_member:
        return Status(200, PublicRsvpPhoneCheckOut(status=PublicRsvpPhoneStatus.EXISTING))
    if event.rsvps.filter(user=user).exists():
        if user.email:
            _send_recognized_login_link(request, user)
        return Status(200, PublicRsvpPhoneCheckOut(status=PublicRsvpPhoneStatus.EXISTING))
    if user.email and user.event_rsvps.exists():
        _send_recognized_login_link(request, user)
        return Status(200, PublicRsvpPhoneCheckOut(status=PublicRsvpPhoneStatus.EXISTING))
    return Status(200, PublicRsvpPhoneCheckOut(status=PublicRsvpPhoneStatus.NEW))


@router.post(
    "/public/events/{event_id}/rsvp/",
    response={200: PublicRsvpOut, 400: ErrorOut, 404: ErrorOut, 409: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="5/h")
def submit_public_rsvp(request, event_id, payload: PublicRsvpIn):
    event = _load_public_rsvp_event(event_id)

    # Honeypot trip — decoy 200 before validation, so bots get no feedback.
    if payload.website.strip():
        audit_log(
            logging.WARNING,
            "public_rsvp_honeypot_tripped",
            request,
            target_type="event",
            target_id=str(event_id),
        )
        return Status(200, _public_rsvp_decoy(event, payload.status, payload.has_plus_one))

    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()
    validate_display_name(first_name, field="first_name")
    if last_name:
        validate_display_name(last_name, field="last_name")
    validated_phone = validate_phone(payload.phone_number, PUBLIC_FORM_PHONE_REGION)
    normalized_email = payload.email.strip().lower()
    _validate_rsvp_status(payload.status)

    with transaction.atomic():
        user = _resolve_non_member(
            request=request,
            first_name=first_name,
            last_name=last_name,
            email=normalized_email,
            phone=validated_phone,
        )
        final_status, promoted_user_ids = _apply_rsvp_in_transaction(
            event.id, user, payload.status, payload.has_plus_one
        )
        token = NonMemberRsvpToken.issue_or_extend(user)

    audit_log(
        logging.INFO,
        "public_rsvp_created",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"user_id": str(user.pk), "status": final_status},
    )

    _post_rsvp_comment(event.id, user, final_status, payload.comment)

    waitlisted = final_status == RSVPStatus.WAITLISTED
    _send_confirmation_email(request, event, user, token.token, waitlisted)
    _email_promoted_non_members(request, event, promoted_user_ids)

    fresh_event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .get(id=event.id)
    )
    broadcast_capacity_change(event.id)
    final_rsvp = user.event_rsvps.get(event=fresh_event)
    return Status(
        200,
        PublicRsvpOut(
            event=_event_out(fresh_event, user),
            rsvp=PublicRsvpStateOut(status=final_rsvp.status, has_plus_one=final_rsvp.has_plus_one),
            rsvp_token=token.token,
        ),
    )
