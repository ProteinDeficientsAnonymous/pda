import pytest
from notifications.event_unpublished_email import (
    EventUnpublishedEmailDetails,
    send_event_unpublished_email,
)
from notifications.models import Notification, NotificationType
from notifications.service import create_event_unpublished_notifications

from tests._events import make_event
from tests._users import make_user


def test_sends_unpublished_email(fake_email_sender):
    send_event_unpublished_email(
        sender=fake_email_sender,
        details=EventUnpublishedEmailDetails(
            to="guest@e.com", display_name="Sam", event_title="Book Club", event_when="Oct 12"
        ),
    )

    sent = fake_email_sender.send.call_args.kwargs
    assert sent["to"] == "guest@e.com"
    assert sent["subject"] == "book club was unpublished"
    assert "book club" in sent["text"]
    assert "hi sam" in sent["text"]
    assert "book club on oct 12 has been unpublished" in sent["text"]


def test_unpublished_email_omits_tbd_time(fake_email_sender):
    send_event_unpublished_email(
        sender=fake_email_sender,
        details=EventUnpublishedEmailDetails(
            to="guest@e.com", display_name="Sam", event_title="Book Club", event_when=""
        ),
    )

    sent = fake_email_sender.send.call_args.kwargs
    assert "book club has been unpublished" in sent["text"]
    assert "book club</strong> has been unpublished" in sent["html"]


@pytest.mark.django_db
def test_creates_unpublished_notifications(test_user):
    recipient = make_user()
    event = make_event(title="book club", created_by=test_user)
    create_event_unpublished_notifications(event, [str(recipient.pk)])

    notification = Notification.objects.get(recipient=recipient)
    assert notification.notification_type == NotificationType.EVENT_UNPUBLISHED
    assert notification.event == event
