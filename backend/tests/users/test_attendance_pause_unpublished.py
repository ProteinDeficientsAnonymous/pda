import pytest
from community.models import EventRSVP, EventStatus, RSVPStatus
from notifications.models import Notification, NotificationType
from tests._events import make_event, make_rsvp
from tests._users import make_user
from users import _attendance_pause
from users._attendance_pause import apply_attendance_pause


@pytest.fixture
def guest(db):
    return make_user(email="guest@e.com")


@pytest.fixture
def drafted_event(member, guest):
    event = make_event(title="Book Club", created_by=member)
    make_rsvp(event, member)
    make_rsvp(event, guest, RSVPStatus.MAYBE)
    return event


@pytest.mark.django_db
class TestUnpublishedGuestNotice:
    def test_notifies_and_emails_guests(
        self, rf, member, drafted_event, fake_email_sender, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            apply_attendance_pause(rf.get("/"), member)

        notification = Notification.objects.get(
            notification_type=NotificationType.EVENT_UNPUBLISHED
        )
        assert notification.recipient.email == "guest@e.com"
        assert notification.event == drafted_event
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == "guest@e.com"
        assert sent["subject"] == "book club was unpublished"

    def test_skips_cant_go_guests(
        self, rf, member, guest, drafted_event, django_capture_on_commit_callbacks
    ):
        EventRSVP.objects.filter(user=guest).update(status=RSVPStatus.CANT_GO)

        with django_capture_on_commit_callbacks(execute=True):
            apply_attendance_pause(rf.get("/"), member)

        assert not Notification.objects.filter(
            notification_type=NotificationType.EVENT_UNPUBLISHED
        ).exists()

    def test_removes_invite_notifications(
        self, rf, member, guest, drafted_event, django_capture_on_commit_callbacks
    ):
        Notification.objects.create(
            recipient=guest, event=drafted_event, notification_type=NotificationType.EVENT_INVITE
        )

        with django_capture_on_commit_callbacks(execute=True):
            apply_attendance_pause(rf.get("/"), member)

        assert not Notification.objects.filter(
            event=drafted_event, notification_type=NotificationType.EVENT_INVITE
        ).exists()

    @pytest.mark.usefixtures("drafted_event")
    def test_failed_notification_still_emails(
        self, rf, member, fake_email_sender, monkeypatch, django_capture_on_commit_callbacks
    ):
        def boom(*_args):
            raise RuntimeError("boom")

        monkeypatch.setattr(_attendance_pause, "create_event_unpublished_notifications", boom)

        with django_capture_on_commit_callbacks(execute=True):
            apply_attendance_pause(rf.get("/"), member)

        assert fake_email_sender.send.call_args.kwargs["to"] == "guest@e.com"

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
