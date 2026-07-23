import pytest
from community._checkin_nudge import (
    due_checkin_nudge_events,
    send_checkin_nudge,
    send_due_checkin_nudges,
)
from community.models import Event, EventStatus, EventType, FeatureFlag, FeatureFlagState
from django.utils import timezone
from notifications.models import Notification, NotificationType
from users.models import User


def _make_event(**kwargs):
    defaults = {
        "title": "Club Meetup",
        "event_type": EventType.CLUB,
        "status": EventStatus.ACTIVE,
        "rsvp_enabled": True,
        "start_datetime": timezone.now(),
    }
    defaults.update(kwargs)
    return Event.objects.create(**defaults)


@pytest.mark.django_db
class TestDueCheckinNudgeEvents:
    def test_includes_club_and_official_started_events(self, test_user, db):
        club = _make_event(created_by=test_user, event_type=EventType.CLUB)
        official = _make_event(
            created_by=test_user, event_type=EventType.OFFICIAL, title="Official"
        )
        due = list(due_checkin_nudge_events(timezone.now()))
        assert club in due
        assert official in due

    def test_excludes_community_events(self, test_user, db):
        _make_event(created_by=test_user, event_type=EventType.COMMUNITY)
        assert list(due_checkin_nudge_events(timezone.now())) == []

    def test_excludes_non_active_status(self, test_user, db):
        _make_event(created_by=test_user, status=EventStatus.CANCELLED)
        assert list(due_checkin_nudge_events(timezone.now())) == []

    def test_excludes_rsvp_disabled(self, test_user, db):
        _make_event(created_by=test_user, rsvp_enabled=False)
        assert list(due_checkin_nudge_events(timezone.now())) == []

    def test_excludes_not_yet_started(self, test_user, db):
        _make_event(
            created_by=test_user, start_datetime=timezone.now() + timezone.timedelta(minutes=5)
        )
        assert list(due_checkin_nudge_events(timezone.now())) == []

    def test_excludes_started_too_long_ago(self, test_user, db):
        _make_event(
            created_by=test_user, start_datetime=timezone.now() - timezone.timedelta(hours=2)
        )
        assert list(due_checkin_nudge_events(timezone.now())) == []

    def test_includes_event_just_within_window(self, test_user, db):
        event = _make_event(
            created_by=test_user, start_datetime=timezone.now() - timezone.timedelta(minutes=59)
        )
        assert list(due_checkin_nudge_events(timezone.now())) == [event]

    def test_excludes_already_nudged(self, test_user, db):
        _make_event(created_by=test_user, checkin_nudge_sent_at=timezone.now())
        assert list(due_checkin_nudge_events(timezone.now())) == []


@pytest.mark.django_db
class TestSendCheckinNudge:
    def test_notifies_and_emails_creator_and_cohosts(self, test_user, fake_email_sender, db):
        cohost = User.objects.create_user(
            phone_number="+12025556001",
            password="cohostpass",
            first_name="Cohost",
            last_name="",
            email="cohost@example.com",
        )
        test_user.email = "creator@example.com"
        test_user.save(update_fields=["email"])
        event = _make_event(created_by=test_user, title="Vegan Potluck")
        event.co_hosts.add(cohost)

        send_checkin_nudge(event)

        notifs = Notification.objects.filter(notification_type=NotificationType.CHECKIN_NUDGE)
        assert notifs.count() == 2
        recipients = {n.recipient_id for n in notifs}
        assert recipients == {test_user.id, cohost.id}
        assert "vegan potluck" in notifs.first().message.lower()

        assert fake_email_sender.send.call_count == 2
        sent_to = {c.kwargs["to"] for c in fake_email_sender.send.call_args_list}
        assert sent_to == {"creator@example.com", "cohost@example.com"}

        event.refresh_from_db()
        assert event.checkin_nudge_sent_at is not None

    def test_skips_recipients_with_no_email(self, test_user, fake_email_sender, db):
        test_user.email = ""
        test_user.save(update_fields=["email"])
        event = _make_event(created_by=test_user)

        send_checkin_nudge(event)

        fake_email_sender.send.assert_not_called()
        event.refresh_from_db()
        assert event.checkin_nudge_sent_at is not None

    def test_does_not_notify_non_host_users(self, test_user, fake_email_sender, db):
        other = User.objects.create_user(
            phone_number="+12025556002", password="pw", first_name="Other", last_name=""
        )
        event = _make_event(created_by=test_user)

        send_checkin_nudge(event)

        notifs = Notification.objects.filter(notification_type=NotificationType.CHECKIN_NUDGE)
        assert notifs.count() == 1
        assert not notifs.filter(recipient=other).exists()

    def test_already_claimed_event_is_not_resent(self, test_user, fake_email_sender, db):
        test_user.email = "creator@example.com"
        test_user.save(update_fields=["email"])
        event = _make_event(created_by=test_user, checkin_nudge_sent_at=timezone.now())

        assert send_checkin_nudge(event) is False
        fake_email_sender.send.assert_not_called()
        assert (
            Notification.objects.filter(notification_type=NotificationType.CHECKIN_NUDGE).count()
            == 0
        )

    def test_email_links_to_attendance_page(self, test_user, fake_email_sender, db):
        test_user.email = "creator@example.com"
        test_user.save(update_fields=["email"])
        event = _make_event(created_by=test_user)

        send_checkin_nudge(event)

        sent = fake_email_sender.send.call_args.kwargs
        assert f"/events/{event.pk}/attendance" in sent["html"]
        assert f"/events/{event.pk}/attendance" in sent["text"]


@pytest.mark.django_db
class TestSendDueCheckinNudges:
    def test_noop_when_flag_off(self, test_user, fake_email_sender, db):
        _make_event(created_by=test_user)
        assert send_due_checkin_nudges() == 0
        fake_email_sender.send.assert_not_called()
        assert (
            Notification.objects.filter(notification_type=NotificationType.CHECKIN_NUDGE).count()
            == 0
        )

    def test_sends_and_stamps_when_flag_on(self, test_user, fake_email_sender, db):
        FeatureFlagState.objects.create(key=FeatureFlag.HOST_ATTENDANCE_REPORT, enabled=True)
        event = _make_event(created_by=test_user)

        count = send_due_checkin_nudges()

        assert count == 1
        event.refresh_from_db()
        assert event.checkin_nudge_sent_at is not None

    def test_idempotent_across_runs(self, test_user, fake_email_sender, db):
        FeatureFlagState.objects.create(key=FeatureFlag.HOST_ATTENDANCE_REPORT, enabled=True)
        _make_event(created_by=test_user)

        assert send_due_checkin_nudges() == 1
        assert send_due_checkin_nudges() == 0
        assert (
            Notification.objects.filter(notification_type=NotificationType.CHECKIN_NUDGE).count()
            == 1
        )
