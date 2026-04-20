"""Public endpoint for invited users to re-request a magic login link."""

import logging
from datetime import timedelta

from config.audit import audit_log
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field

from community._field_limits import FieldLimit
from community._shared import ErrorOut, _validate_phone, logger  # noqa: F401

router = Router()


class RequestLoginLinkIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)


class RequestLoginLinkOut(BaseModel):
    detail: str


_REQUEST_LINK_RESPONSE = "if you've been invited, an admin will be in touch with your login link"


@router.post("/request-login-link/", response={200: RequestLoginLinkOut}, auth=None)
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
    except ValueError:
        audit_log(
            logging.INFO,
            "magic_link_request_skipped_invalid_phone",
            request,
        )
        return Status(200, RequestLoginLinkOut(detail=_REQUEST_LINK_RESPONSE))

    user = User.objects.filter(phone_number=normalized, archived_at__isnull=True).first()
    if user is None:
        audit_log(
            logging.INFO,
            "magic_link_request_skipped_unknown_phone",
            request,
        )
        return Status(200, RequestLoginLinkOut(detail=_REQUEST_LINK_RESPONSE))

    if user.login_link_requested:
        audit_log(
            logging.INFO,
            "magic_link_request_skipped_already_pending",
            request,
            target_type="user",
            target_id=str(user.pk),
        )
        return Status(200, RequestLoginLinkOut(detail=_REQUEST_LINK_RESPONSE))

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
        return Status(200, RequestLoginLinkOut(detail=_REQUEST_LINK_RESPONSE))

    _create_magic_token(user)
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

    return Status(200, RequestLoginLinkOut(detail=_REQUEST_LINK_RESPONSE))
