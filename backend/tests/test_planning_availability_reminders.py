from datetime import datetime, timedelta

import pytest
from community.models import BiannualInterest, PlanningAvailability, PlanningYear
from community.planning._notify import notify_availability_open
from community.planning.reminders import send_availability_reminders
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from notifications.models import Notification, NotificationType
from users.permissions import PermissionKey

from tests._users import make_user

VIEW = PermissionKey.VIEW_EVENT_PLANNING
DAY = timedelta(days=1)
OPENED_AT = datetime(2026, 10, 1, 9, 0, tzinfo=settings.COMMUNITY_TZ)
YEAR_STARTS = datetime(2027, 1, 1, tzinfo=settings.COMMUNITY_TZ)


@pytest.fixture
def opened(year):
    PlanningYear.objects.filter(pk=year.pk).update(availability_opened_at=OPENED_AT)
    year.refresh_from_db()
    return year


@pytest.fixture
def waiting(db):
    return make_user(VIEW, email="planner@example.com")


@pytest.mark.django_db
class TestAvailabilityOpenNotice:
    def test_every_planner_gets_a_notice_and_an_email(self, year, waiting, fake_email_sender):
        coordinator = make_user(PermissionKey.MANAGE_EVENT_PLANNING)
        no_email = make_user(VIEW, email="")
        make_user(email="member@example.com")

        with TestCase.captureOnCommitCallbacks(execute=True):
            notify_availability_open(year, coordinator)

        notices = Notification.objects.order_by("recipient__email")
        assert [n.recipient for n in notices] == [no_email, waiting]
        notice = notices[0]
        assert notice.notification_type == NotificationType.PLANNING_AVAILABILITY
        assert notice.message == "when can you plan in 2027? 🌱 tap to fill in your availability"
        assert notice.related_user == coordinator
        fake_email_sender.send.assert_called_once()
        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == "planner@example.com"
        assert kwargs["subject"] == "when can you plan in 2027?"
        assert f"{settings.FRONTEND_BASE_URL}/admin/planning?tab=availability" in kwargs["text"]


@pytest.mark.django_db
class TestAvailabilityReminders:
    def test_weekly_after_opening_with_an_hour_of_drift_slack(
        self, opened, waiting, fake_email_sender
    ):
        assert send_availability_reminders(OPENED_AT + 6 * DAY) == 0
        assert send_availability_reminders(OPENED_AT + 7 * DAY - timedelta(minutes=45)) == 1
        assert send_availability_reminders(OPENED_AT + 7 * DAY) == 0
        assert send_availability_reminders(OPENED_AT + 13 * DAY) == 0
        assert send_availability_reminders(OPENED_AT + 14 * DAY) == 1
        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == "planner@example.com"
        assert kwargs["subject"] == "still need your 2027 planning availability"
        assert f"{settings.FRONTEND_BASE_URL}/admin/planning?tab=availability" in kwargs["text"]

    def test_submitting_stops_reminders(self, opened, waiting, fake_email_sender):
        PlanningAvailability.objects.create(
            planning_year=opened, user=waiting, biannual_interest=BiannualInterest.NO
        )
        assert send_availability_reminders(OPENED_AT + 7 * DAY) == 0
        fake_email_sender.send.assert_not_called()

    def test_submitting_another_year_does_not_count(self, opened, waiting, fake_email_sender):
        other = PlanningYear.create_with_default_slots(2026)
        PlanningAvailability.objects.create(
            planning_year=other, user=waiting, biannual_interest=BiannualInterest.NO
        )
        assert send_availability_reminders(OPENED_AT + 7 * DAY) == 1

    def test_not_sent_before_opening(self, year, waiting, fake_email_sender):
        assert send_availability_reminders(OPENED_AT + 30 * DAY) == 0

    def test_stops_once_the_year_starts(self, opened, waiting, fake_email_sender):
        assert send_availability_reminders(YEAR_STARTS - timedelta(minutes=1)) == 1
        assert send_availability_reminders(YEAR_STARTS + 7 * DAY) == 0

    @pytest.mark.parametrize("fields", [{"email": ""}, {"email": None}])
    def test_skips_planners_without_email(self, opened, fake_email_sender, fields):
        make_user(VIEW, **fields)
        assert send_availability_reminders(OPENED_AT + 7 * DAY) == 0

    def test_skips_non_planners(self, opened, fake_email_sender):
        make_user(email="member@example.com")
        assert send_availability_reminders(OPENED_AT + 7 * DAY) == 0

    def test_failed_send_is_not_counted(self, opened, waiting, fake_email_sender):
        fake_email_sender.send.side_effect = RuntimeError("provider down")
        assert send_availability_reminders(OPENED_AT + 7 * DAY) == 0

    def test_command_reports_availability_reminders(
        self, opened, waiting, fake_email_sender, capsys, monkeypatch
    ):
        monkeypatch.setattr("django.utils.timezone.now", lambda: OPENED_AT + 7 * DAY)
        call_command("send_planning_reminders")
        assert "1 availability reminder(s)" in capsys.readouterr().out
