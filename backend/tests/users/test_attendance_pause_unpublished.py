from datetime import timedelta

import pytest
from community.models import Event, EventRSVP, EventStatus, RSVPStatus
from django.utils import timezone
from notifications.models import Notification, NotificationType
from users._attendance_pause import apply_attendance_pause


@pytest.fixture
def drafted_event(member, other_user):
    other_user.email = "guest@e.com"
    other_user.save(update_fields=["email"])
    event = Event.objects.create(
        title="Book Club",
        start_datetime=timezone.now() + timedelta(days=3),
        created_by=member,
        status=EventStatus.ACTIVE,
    )
    EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.ATTENDING)
    EventRSVP.objects.create(event=event, user=other_user, status=RSVPStatus.MAYBE)
    return event


@pytest.mark.django_db
class TestUnpublishedGuestNotice:
    def test_notifies_and_emails_guests(
        self,
        rf,
        member,
        other_user,
        drafted_event,
        fake_email_sender,
        django_capture_on_commit_callbacks,
    ):
        with django_capture_on_commit_callbacks(execute=True):
            apply_attendance_pause(rf.get("/"), member)

        notification = Notification.objects.get(
            notification_type=NotificationType.EVENT_UNPUBLISHED
        )
        assert notification.recipient == other_user
        assert notification.event == drafted_event
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == "guest@e.com"
        assert sent["subject"] == "book club was unpublished"

    def test_skips_cant_go_guests(
        self, rf, member, other_user, drafted_event, django_capture_on_commit_callbacks
    ):
        EventRSVP.objects.filter(user=other_user).update(status=RSVPStatus.CANT_GO)

        with django_capture_on_commit_callbacks(execute=True):
            apply_attendance_pause(rf.get("/"), member)

        assert not Notification.objects.filter(
            notification_type=NotificationType.EVENT_UNPUBLISHED
        ).exists()

    def test_failed_send_keeps_the_pause(
        self, rf, member, drafted_event, fake_email_sender, django_capture_on_commit_callbacks
    ):
        fake_email_sender.send.side_effect = RuntimeError("boom")

        with django_capture_on_commit_callbacks(execute=True):
            apply_attendance_pause(rf.get("/"), member)

        member.refresh_from_db()
        drafted_event.refresh_from_db()
        assert member.attendance_paused_at is not None
        assert drafted_event.status == EventStatus.DRAFT
