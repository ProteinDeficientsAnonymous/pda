"""Admin-triggered magic login link generation."""

import logging
from datetime import timedelta

from config.audit import audit_log
from django.db import transaction
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from notifications.models import Notification, NotificationType
from notifications.service import _notify_users

from users._helpers import _create_magic_token
from users.models import MagicLoginToken, User
from users.permissions import PermissionKey
from users.schemas import ErrorOut, ResetPasswordOut

router = Router()


@router.post(
    "/users/{user_id}/magic-link/",
    response={200: ResetPasswordOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def generate_magic_link(request, user_id: str):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="user",
            target_id=user_id,
            details={
                "endpoint": "generate_magic_link",
                "required_permission": PermissionKey.MANAGE_USERS,
            },
        )
        return Status(403, ErrorOut(detail="Permission denied."))

    with transaction.atomic():
        try:
            user = User.objects.select_for_update().get(pk=user_id)
        except User.DoesNotExist:
            return Status(404, ErrorOut(detail="User not found."))

        # If another admin generated a link in the last 5 minutes, reuse it
        # instead of creating a duplicate. Resolves the race where multiple
        # admins respond to the same magic-link request notification.
        recent_token = (
            MagicLoginToken.objects.filter(
                user=user,
                used=False,
                created_at__gte=timezone.now() - timedelta(minutes=5),
            )
            .order_by("-created_at")
            .first()
        )
        if recent_token is not None and not user.login_link_requested:
            audit_log(
                logging.INFO,
                "magic_link_already_handled",
                request,
                target_type="user",
                target_id=user_id,
            )
            return Status(
                200,
                ResetPasswordOut(
                    detail="Magic login link was already generated recently — reusing it.",
                    magic_link_token=str(recent_token.token),
                ),
            )

        user.set_unusable_password()
        user.needs_onboarding = True
        was_requested = user.login_link_requested
        user.login_link_requested = False
        user.save(update_fields=["password", "needs_onboarding", "login_link_requested"])

        cleared_count = 0
        recipient_ids: list[str] = []
        if was_requested:
            cleared_count = Notification.objects.filter(
                notification_type=NotificationType.MAGIC_LINK_REQUEST,
                related_user=user,
                is_read=False,
            ).update(is_read=True)
            recipient_ids = list(
                Notification.objects.filter(
                    notification_type=NotificationType.MAGIC_LINK_REQUEST,
                    related_user=user,
                ).values_list("recipient_id", flat=True)
            )
        magic_token = _create_magic_token(user)

    if recipient_ids:
        _notify_users(str(rid) for rid in recipient_ids)
        audit_log(
            logging.INFO,
            "magic_link_notifications_cleared",
            request,
            target_type="user",
            target_id=user_id,
            details={"count": cleared_count},
        )
    audit_log(
        logging.INFO,
        "magic_link_generated",
        request,
        target_type="user",
        target_id=user_id,
    )
    return Status(
        200,
        ResetPasswordOut(
            detail="Magic login link generated.",
            magic_link_token=magic_token,
        ),
    )
