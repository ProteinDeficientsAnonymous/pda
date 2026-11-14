from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from community.models import AssignmentStatus, EventStatus, SlotAssignment
from community.planning._notify import notify_upcoming
from community.planning.reminders import send_proposal_reminders, send_upcoming_notices
from django.conf import settings
from django.core.management import call_command
from notifications.email_sender import SendResult
from notifications.models import Notification, NotificationType
from users.models import MembershipStatus
from users.permissions import PermissionKey

from tests._events import make_event
from tests._users import grant, make_attendance_paused, make_user

VIEW = PermissionKey.VIEW_EVENT_PLANNING
DAY = timedelta(days=1)
PROPOSED_AT = datetime(2026, 12, 1, 15, 0, tzinfo=settings.COMMUNITY_TZ)
MONTH_START = datetime(2027, 1, 1, tzinfo=settings.COMMUNITY_TZ)
WINDOW_OPENS = MONTH_START - 42 * DAY


@pytest.fixture
def slot(year):
    return year.slots.first()


@pytest.fixture
def proposed(slot):
    planner = make_user(VIEW, email="planner@example.com")
    return SlotAssignment.objects.create(slot=slot, user=planner, proposed_at=PROPOSED_AT)


@pytest.mark.django_db
class TestProposalReminders:
    def test_first_reminder_at_day_three_not_day_two(self, proposed, slot, fake_email_sender):
        assert send_proposal_reminders(PROPOSED_AT + 2 * DAY) == 0
        fake_email_sender.send.assert_not_called()
        assert send_proposal_reminders(PROPOSED_AT + 3 * DAY) == 1
        assert send_proposal_reminders(PROPOSED_AT + 3 * DAY) == 0
        proposed.refresh_from_db()
        assert (proposed.reminder_count, proposed.last_reminded_at) == (1, PROPOSED_AT + 3 * DAY)
        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == "planner@example.com"
        assert kwargs["subject"] == f"still need an answer: can you plan {slot.label}?"
        assert f"{settings.FRONTEND_BASE_URL}/admin/planning" in kwargs["text"]
        assert not Notification.objects.exists()

    def test_second_reminder_at_day_six_with_an_hour_of_drift_slack(
        self, proposed, fake_email_sender
    ):
        send_proposal_reminders(PROPOSED_AT + 3 * DAY - timedelta(minutes=30))
        assert send_proposal_reminders(PROPOSED_AT + 5 * DAY) == 0
        assert send_proposal_reminders(PROPOSED_AT + 6 * DAY - timedelta(minutes=45)) == 1
        proposed.refresh_from_db()
        assert proposed.reminder_count == 2

    def test_stops_once_month_has_started(self, proposed, fake_email_sender):
        start = datetime(2027, 1, 1, tzinfo=settings.COMMUNITY_TZ)
        assert send_proposal_reminders(start - timedelta(minutes=1)) == 1
        assert send_proposal_reminders(start + 3 * DAY) == 0
        assert send_proposal_reminders(start) == 0

    def test_not_proposed_statuses_skipped(self, proposed, fake_email_sender):
        for status in (AssignmentStatus.COMMITTED, AssignmentStatus.DECLINED):
            SlotAssignment.objects.filter(pk=proposed.pk).update(status=status)
            assert send_proposal_reminders(PROPOSED_AT + 3 * DAY) == 0

    def test_no_reminder_after_permission_removed(self, proposed, fake_email_sender):
        proposed.user.roles.clear()
        assert send_proposal_reminders(PROPOSED_AT + 3 * DAY) == 0
        fake_email_sender.send.assert_not_called()

    @pytest.mark.parametrize(
        "fields",
        [{"membership_status": MembershipStatus.ATTENDANCE_PAUSED}, {"email": ""}],
    )
    def test_paused_or_emailless_planner_skipped(self, proposed, fields, fake_email_sender):
        type(proposed.user).objects.filter(pk=proposed.user_id).update(**fields)
        assert send_proposal_reminders(PROPOSED_AT + 3 * DAY) == 0

    def test_failed_send_is_retried_next_run(self, proposed, fake_email_sender):
        fake_email_sender.send.return_value = SendResult(success=False, error="nope")
        now = PROPOSED_AT + 3 * DAY
        assert send_proposal_reminders(now) == 0
        proposed.refresh_from_db()
        assert (proposed.reminder_count, proposed.last_reminded_at) == (0, None)
        fake_email_sender.send.return_value = SendResult(success=True, provider_message_id="x")
        assert send_proposal_reminders(now + DAY) == 1


@pytest.fixture
def committed(slot):
    planner = make_user(VIEW, email="committed@example.com")
    return SlotAssignment.objects.create(
        slot=slot, user=planner, status=AssignmentStatus.COMMITTED, proposed_at=PROPOSED_AT
    )


@pytest.mark.django_db
class TestUpcomingNotices:
    def test_fires_from_six_weeks_out_not_before(self, committed, fake_email_sender):
        assert send_upcoming_notices(WINDOW_OPENS - timedelta(minutes=1)) == 0
        assert send_upcoming_notices(WINDOW_OPENS) == 1

    def test_fires_once(self, committed, fake_email_sender):
        assert send_upcoming_notices(WINDOW_OPENS + 5 * DAY) == 1
        assert send_upcoming_notices(WINDOW_OPENS + 6 * DAY) == 0
        committed.refresh_from_db()
        assert committed.upcoming_notified_at == WINDOW_OPENS + 5 * DAY
        assert Notification.objects.count() == 1

    def test_fires_for_commit_made_inside_window(self, committed, fake_email_sender):
        assert send_upcoming_notices(MONTH_START - 3 * DAY) == 1

    def test_not_once_month_has_started(self, committed, fake_email_sender):
        assert send_upcoming_notices(MONTH_START) == 0

    def test_only_committed_rows(self, committed, fake_email_sender):
        for status in (AssignmentStatus.PROPOSED, AssignmentStatus.DECLINED):
            SlotAssignment.objects.filter(pk=committed.pk).update(status=status)
            assert send_upcoming_notices(WINDOW_OPENS) == 0

    def test_no_notice_after_permission_removed(self, committed, fake_email_sender):
        committed.user.roles.clear()
        assert send_upcoming_notices(WINDOW_OPENS) == 0
        assert not Notification.objects.exists()
        fake_email_sender.send.assert_not_called()

    def test_no_notice_when_planner_paused(self, slot, fake_email_sender):
        paused = make_attendance_paused(email="paused@example.com")
        grant(paused, VIEW)
        SlotAssignment.objects.create(
            slot=slot, user=paused, status=AssignmentStatus.COMMITTED, proposed_at=PROPOSED_AT
        )
        assert send_upcoming_notices(WINDOW_OPENS) == 0
        assert not Notification.objects.exists()

    def test_skipped_when_slot_has_live_event(self, committed, slot, fake_email_sender):
        slot.event = make_event()
        slot.save(update_fields=["event"])
        assert send_upcoming_notices(WINDOW_OPENS) == 0

    def test_fires_when_linked_event_was_deleted(self, committed, slot, fake_email_sender):
        slot.event = make_event(status=EventStatus.DELETED)
        slot.save(update_fields=["event"])
        assert send_upcoming_notices(WINDOW_OPENS) == 1

    def test_notifies_in_app_and_by_email(self, committed, slot, fake_email_sender):
        send_upcoming_notices(WINDOW_OPENS)
        notification = Notification.objects.get(recipient=committed.user)
        assert notification.notification_type == NotificationType.PLANNING_UPCOMING
        assert notification.message == f"{slot.label} is coming up — time to create the event"
        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == "committed@example.com"
        assert kwargs["subject"] == f"{slot.label} is coming up"
        assert "create the event" in kwargs["text"]
        assert "create the event" in kwargs["html"]
        assert f"{settings.FRONTEND_BASE_URL}/admin/planning" in kwargs["text"]

    def test_no_email_address_still_notifies_in_app(self, committed, fake_email_sender):
        type(committed.user).objects.filter(pk=committed.user_id).update(email="")
        assert send_upcoming_notices(WINDOW_OPENS) == 1
        assert Notification.objects.filter(recipient=committed.user).count() == 1
        fake_email_sender.send.assert_not_called()

    def test_notice_failure_rolls_back_stamp_and_batch_continues(self, committed, slot):
        other = make_user(VIEW, email="other@example.com")
        done = SlotAssignment.objects.create(
            slot=slot, user=other, status=AssignmentStatus.COMMITTED, proposed_at=PROPOSED_AT
        )

        def flaky(assignment):
            if assignment.pk == committed.pk:
                raise RuntimeError("boom")
            notify_upcoming(assignment)

        with patch("community.planning.reminders.notify_upcoming", side_effect=flaky):
            assert send_upcoming_notices(WINDOW_OPENS) == 1
        committed.refresh_from_db()
        done.refresh_from_db()
        assert committed.upcoming_notified_at is None
        assert done.upcoming_notified_at == WINDOW_OPENS
        assert send_upcoming_notices(WINDOW_OPENS + DAY) == 1

    def test_failed_email_keeps_stamp_so_it_is_not_resent(self, committed, fake_email_sender):
        fake_email_sender.send.return_value = SendResult(success=False, error="nope")
        assert send_upcoming_notices(WINDOW_OPENS) == 1
        assert send_upcoming_notices(WINDOW_OPENS + DAY) == 0


@pytest.mark.django_db
def test_command_reports_both_counts(proposed, committed, fake_email_sender, capsys):
    SlotAssignment.objects.filter(pk=proposed.pk).update(proposed_at=PROPOSED_AT - 400 * DAY)
    with patch("django.utils.timezone.now", return_value=WINDOW_OPENS + DAY):
        call_command("send_planning_reminders")
    out = capsys.readouterr().out
    assert "1 proposal reminder" in out
    assert "1 upcoming notice" in out
