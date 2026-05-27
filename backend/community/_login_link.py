"""Public endpoint for invited users to re-request a magic login link."""

import logging
from datetime import timedelta

from config.audit import audit_log
from config.ratelimit import client_ip, rate_limit
from django.conf import settings
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from notifications._email_helpers import send_magic_login_email
from notifications.email_sender import get_email_sender
from pydantic import BaseModel, Field

from community._field_limits import FieldLimit
from community._shared import ErrorOut, _validate_phone, logger  # noqa: F401
from community._validation import ValidationException

router = Router()


class RequestLoginLinkIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)


class RequestLoginLinkOut(BaseModel):
    detail: str
    # "email" when an email was sent; "admin" for every other case (no email
    # on file, send failed, unknown phone, etc.). Bundling the unknown-phone
    # case into "admin" weakens anti-enumeration slightly — an attacker who
    # sees "email" learns the account exists AND has an email — but the
    # honest UX of telling email-having users to check their inbox is worth
    # the small leak, especially given the 5/m rate limit on this endpoint.
    delivery: str


_DELIVERY_EMAIL = "email"
_DELIVERY_ADMIN = "admin"
_EMAIL_RESPONSE = (
    "if there's an account for that number, we sent a login link to the email on file — "
    "check your inbox, including spam"
)
_ADMIN_RESPONSE = (
    "if there's an account for that number, an admin will follow up with your login link"
)


@router.post(
    "/request-login-link/",
    response={200: RequestLoginLinkOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="5/m")
def request_login_link(request, payload: RequestLoginLinkIn):
    """Unauthenticated endpoint for invited users to re-request a magic login link.

    Always returns 200 to prevent phone number enumeration.
    If a User exists, generates a magic link token and notifies admins.
    """
    from notifications.service import create_magic_link_request_notifications
    from users._helpers import _create_magic_token
    from users.models import MagicLoginToken, User

    try:
        normalized = _validate_phone(payload.phone_number)
    except ValidationException:
        audit_log(
            logging.INFO,
            "magic_link_request_skipped_invalid_phone",
            request,
        )
        return Status(200, RequestLoginLinkOut(detail=_ADMIN_RESPONSE, delivery=_DELIVERY_ADMIN))

    user = User.objects.filter(phone_number=normalized, archived_at__isnull=True).first()
    if user is None:
        audit_log(
            logging.INFO,
            "magic_link_request_skipped_unknown_phone",
            request,
        )
        return Status(200, RequestLoginLinkOut(detail=_ADMIN_RESPONSE, delivery=_DELIVERY_ADMIN))

    if user.login_link_requested:
        audit_log(
            logging.INFO,
            "magic_link_request_skipped_already_pending",
            request,
            target_type="user",
            target_id=str(user.pk),
        )
        return Status(200, RequestLoginLinkOut(detail=_ADMIN_RESPONSE, delivery=_DELIVERY_ADMIN))

    recent_token_exists = MagicLoginToken.objects.filter(
        user=user,
        created_at__gte=timezone.now() - timedelta(minutes=5),
    ).exists()
    if recent_token_exists:
        audit_log(
            logging.INFO,
            "magic_link_request_skipped_recent_token",
            request,
            target_type="user",
            target_id=str(user.pk),
        )
        return Status(200, RequestLoginLinkOut(detail=_ADMIN_RESPONSE, delivery=_DELIVERY_ADMIN))

    magic_token = _create_magic_token(user)
    user.login_link_requested = True
    user.save(update_fields=["login_link_requested"])

    email_success = _try_email_delivery(request=request, user=user, magic_token=magic_token)
    if email_success:
        return Status(
            200,
            RequestLoginLinkOut(detail=_EMAIL_RESPONSE, delivery=_DELIVERY_EMAIL),
        )

    # No email or send failed — fall through to admin notification.
    try:
        create_magic_link_request_notifications(user)
    except Exception:
        logger.exception("Failed to create magic link request notifications")
    audit_log(
        logging.INFO,
        "magic_link_requested",
        request,
        target_type="user",
        target_id=str(user.pk),
    )

    return Status(200, RequestLoginLinkOut(detail=_ADMIN_RESPONSE, delivery=_DELIVERY_ADMIN))


def _try_email_delivery(*, request, user, magic_token) -> bool:
    """Try delivering the magic link via email.

    Returns True on success, False if we should fall through to the
    admin-notification path. Any unexpected error is logged and treated
    as a failure so the caller still falls through.
    """
    if not user.email:
        return False
    try:
        magic_link_url = f"{settings.FRONTEND_BASE_URL}/magic-login/{magic_token}"
        send_result = send_magic_login_email(
            sender=get_email_sender(),
            to=user.email,
            display_name=user.display_name or "",
            magic_link_url=magic_link_url,
        )
        if send_result.success:
            audit_log(
                logging.INFO,
                "magic_link_email_sent",
                request,
                target_type="user",
                target_id=str(user.pk),
                details={"provider_message_id": send_result.provider_message_id},
            )
            return True
        audit_log(
            logging.WARNING,
            "magic_link_email_failed",
            request,
            target_type="user",
            target_id=str(user.pk),
            details={"error": send_result.error},
        )
        return False
    except Exception:
        logger.exception("Unexpected error sending magic-login email")
        return False
