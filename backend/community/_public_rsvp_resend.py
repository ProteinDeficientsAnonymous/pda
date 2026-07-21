import logging

from config.audit import audit_log
from config.ratelimit import client_ip, rate_limit
from django.conf import settings
from ninja import Router
from ninja.responses import Status
from notifications._email_helpers import send_rsvp_manage_link_email
from notifications.email_sender import get_email_sender
from pydantic import BaseModel, EmailStr, Field
from users.models import PUBLIC_FORM_PHONE_REGION, NonMemberRsvpToken, User, validate_phone

from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community._validation import ValidationException

router = Router()

# Neutral response for every outcome (match, no match, member, honeypot, bad
# phone) so the endpoint never reveals whether an account exists.
_NEUTRAL_RESPONSE = (
    "if that phone and email match a non-member rsvp, we've emailed you a fresh "
    "link — check your inbox, including spam. if you have a member account, "
    "sign in instead"
)


class ResendManageLinkIn(BaseModel):
    email: EmailStr
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    # Honeypot: hidden field humans never fill in. A non-empty value is spam.
    website: str = Field(default="", max_length=FieldLimit.DISPLAY_NAME)


class ResendManageLinkOut(BaseModel):
    detail: str


def _neutral() -> Status:
    return Status(200, ResendManageLinkOut(detail=_NEUTRAL_RESPONSE))


def _find_non_member(phone: str, email: str) -> User | None:
    """Find the non-member User matching this phone (canonical) or email.

    Returns None when there's no match OR the match is a member.
    """
    phone_match = User.objects.filter(phone_number=phone).first()
    email_match = User.objects.filter(email__iexact=email).first() if email else None
    if (phone_match and phone_match.is_member) or (email_match and email_match.is_member):
        return None
    return phone_match or email_match


def _send_manage_link(request, user: User) -> None:
    """Best-effort resend of the non-member's manage link. Failures are logged."""
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
            "public_rsvp_resend_email_failed",
            request,
            target_type="user",
            target_id=str(user.pk),
            details={"error": str(exc)},
        )


@router.post(
    "/public/my-rsvps/resend/",
    response={200: ResendManageLinkOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="3/h")
def resend_manage_link(request, payload: ResendManageLinkIn):
    """Public recovery path: re-send a non-member's manage-rsvp link by phone + email.

    Honeypot trips, bad phones, unknown contacts, and member contacts all
    resolve to the same neutral 200 body; only a matching non-member with an
    email on file is actually sent a link. The response body never reveals
    whether an account exists — the one residual signal is that the match+email
    path sends synchronously, so it's marginally slower; the 3/h IP rate limit
    keeps that timing side channel impractical to exploit.
    """
    if payload.website.strip():
        audit_log(
            logging.WARNING,
            "public_rsvp_resend_honeypot_tripped",
            request,
        )
        return _neutral()

    try:
        validated_phone = validate_phone(payload.phone_number, PUBLIC_FORM_PHONE_REGION)
    except ValidationException:
        return _neutral()
    normalized_email = payload.email.strip().lower()

    user = _find_non_member(validated_phone, normalized_email)
    if user is not None and user.email:
        _send_manage_link(request, user)
        audit_log(
            logging.INFO,
            "public_rsvp_resend_sent",
            request,
            target_type="user",
            target_id=str(user.pk),
        )
    return _neutral()
