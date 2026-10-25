from __future__ import annotations

from typing import TYPE_CHECKING

from users.models import User
from users.permissions import PermissionKey

from notifications.models import Notification, NotificationType
from notifications.service import notify_users

if TYPE_CHECKING:
    from community.models import Survey


def notify_survey_response(survey: Survey, submitter: User | None) -> None:
    """Ping survey managers that a new response came in; never names the responder."""
    recipients = User.objects.with_permission(PermissionKey.MANAGE_SURVEYS)
    if submitter is not None:
        recipients = recipients.exclude(pk=submitter.pk)
    recipient_ids = [str(pk) for pk in recipients.values_list("pk", flat=True)]
    if not recipient_ids:
        return
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=rid,
                notification_type=NotificationType.SURVEY_RESPONSE,
                survey=survey,
                message=f"new response to {survey.title}",
            )
            for rid in recipient_ids
        ]
    )
    notify_users(recipient_ids)
