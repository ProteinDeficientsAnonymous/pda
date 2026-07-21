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
from notifications.service import create_magic_link_request_notifications
from pydantic import BaseModel, Field
from users._helpers import _create_magic_token
from users.models import (
    PUBLIC_FORM_PHONE_REGION,
    MagicLoginToken,
    MagicLoginTokenSource,
    User,
    validate_phone,
)

from community._field_limits import FieldLimit
from community._shared import ErrorOut, logger  # noqa: F401
from community._validation import ValidationException

router = Router()


class RequestLoginLinkIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)


class RequestLoginLinkOut(BaseModel):
    detail: str
    # "email"    — a fresh link was emailed.
    # "cooldown" — a real account requested a link within the last 5 minutes;
    #              we ask them to check their inbox or wait.
    # "admin"    — every other case (no email on file, send failed, unknown
    #              phone, invalid phone): an admin will follow up.
    # The "email"/"cooldown" responses only occur for real accounts, so they
    # weaken anti-enumeration slightly — but the honest UX is worth the small
    # leak, especially given the 5/m rate limit on this endpoint. Unknown and
    # invalid phones stay in the neutral "admin" bucket.
    delivery: str
    # Seconds until the user may request another link. Only set on the
    # "cooldown" delivery so the client can show an honest countdown; null
    # otherwise.
    retry_after_seconds: int | None = None


_COOLDOWN = timedelta(minutes=2)
_DELIVERY_EMAIL = "email"
_DELIVERY_ADMIN = "admin"
_DELIVERY_COOLDOWN = "cooldown"
_EMAIL_RESPONSE = (
    "if there's an account for that number, we sent a login link to the email on file — "
    "check your inbox, including spam"
)
_ADMIN_RESPONSE = (
    "if there's an account for that number, an admin will follow up with your login link"
)
_COOLDOWN_RESPONSE = (
    "you recently requested a login link — check your inbox, including spam, "
    "or request another in a few minutes"
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
    try:
        normalized = validate_phone(payload.phone_number, PUBLIC_FORM_PHONE_REGION)
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

    # Cooldown: a link was already minted within the last window. Re-requesting
    # is allowed (no permanent block), but we throttle to one fresh link per window
    # and tell the user to check their inbox or wait.
    now = timezone.now()
    recent_token = (
        MagicLoginToken.objects.filter(
            user=user,
            source=MagicLoginTokenSource.SELF_SERVICE,
            created_at__gte=now - _COOLDOWN,
        )
        .order_by("-created_at")
        .first()
    )
    if recent_token is not None:
        audit_log(
            logging.INFO,
            "magic_link_request_skipped_recent_token",
            request,
            target_type="user",
            target_id=str(user.pk),
        )
        retry_after = max(1, round((recent_token.created_at + _COOLDOWN - now).total_seconds()))
        return Status(
            200,
            RequestLoginLinkOut(
                detail=_COOLDOWN_RESPONSE,
                delivery=_DELIVERY_COOLDOWN,
                retry_after_seconds=retry_after,
            ),
        )

    # Invalidate any prior unused links so only the newest one works — avoids
    # multiple valid links floating around the user's inbox.
    MagicLoginToken.objects.filter(user=user, used=False).update(used=True)
    magic_token = _create_magic_token(
        user,
        requires_password_reset=True,
        source=MagicLoginTokenSource.SELF_SERVICE,
    )

    email_success = _try_email_delivery(request=request, user=user, magic_token=magic_token)
    if email_success:
        # Email path: do NOT set login_link_requested — re-requests stay unblocked
        # (the 5-minute cooldown above is the only throttle).
        return Status(
            200,
            RequestLoginLinkOut(detail=_EMAIL_RESPONSE, delivery=_DELIVERY_EMAIL),
        )

    # No email or send failed — fall through to admin notification.
    # login_link_requested dedupes admin-queue notifications for the waiting request.
    user.login_link_requested = True
    user.save(update_fields=["login_link_requested"])
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
            display_name=user.full_name or "",
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
