from datetime import datetime, timedelta

import pytest
from community.models import AssignmentStatus, SlotAssignment
from community.planning.reminders import send_proposal_reminders
from django.conf import settings
from django.core.management import call_command
from notifications.email_sender import SendResult
from notifications.models import Notification
from users.models import MembershipStatus
from users.permissions import PermissionKey

from tests._users import make_user

VIEW = PermissionKey.VIEW_EVENT_PLANNING
DAY = timedelta(days=1)
PROPOSED_AT = datetime(2026, 12, 1, 15, 0, tzinfo=settings.COMMUNITY_TZ)


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


@pytest.mark.django_db
def test_command_reports_count(proposed, fake_email_sender, capsys):
    SlotAssignment.objects.filter(pk=proposed.pk).update(proposed_at=PROPOSED_AT - 400 * DAY)
    call_command("send_planning_reminders")
    assert "1 proposal reminder" in capsys.readouterr().out
