from unittest.mock import MagicMock

import pytest
from community.models import Event
from notifications.email_sender import SendResult
from notifications.event_unpublished_email import (
    EventUnpublishedEmailDetails,
    send_event_unpublished_email,
)
from notifications.models import Notification, NotificationType
from notifications.service import create_event_unpublished_notifications


def test_sends_unpublished_email():
    sender = MagicMock()
    sender.send.return_value = SendResult(success=True)

    send_event_unpublished_email(
        sender=sender,
        details=EventUnpublishedEmailDetails(
            to="guest@e.com", display_name="Sam", event_title="Book Club", event_when="Oct 12"
        ),
    )

    sent = sender.send.call_args.kwargs
    assert sent["to"] == "guest@e.com"
    assert sent["subject"] == "book club was unpublished"
    assert "book club" in sent["text"]
    assert "hi sam" in sent["text"]


@pytest.mark.django_db
def test_creates_unpublished_notifications(test_user, vettor_user):
    event = Event.objects.create(title="book club", created_by=test_user)
    create_event_unpublished_notifications(event, [str(vettor_user.pk)])

    notification = Notification.objects.get(recipient=vettor_user)
    assert notification.notification_type == NotificationType.EVENT_UNPUBLISHED
    assert notification.event == event
