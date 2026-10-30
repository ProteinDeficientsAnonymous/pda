from datetime import datetime, timedelta
from io import StringIO

import pytest
from community._event_feedback_send import (
    due_feedback_events,
    feedback_cutoff,
    feedback_url,
    send_first_requests,
    send_reminders,
)
from community.models import (
    AttendanceStatus,
    Event,
    EventFeedbackRequest,
    EventStatus,
    EventType,
    Survey,
)
from django.conf import settings
from django.core.management import call_command
from notifications.email_sender import SendResult

from tests._event_feedback_helpers import (
    NOW,
    TZ,
    make_ended_event,
    make_rsvp,
)
from tests._users import make_user


def _request(event, user, **extra) -> EventFeedbackRequest:
    return EventFeedbackRequest.objects.create(
        event=event, user=user, token=EventFeedbackRequest.new_token(), **extra
    )


@pytest.mark.django_db
class TestDueFeedbackEvents:
    def test_event_ended_yesterday_included(self, feedback_survey):
        event = make_ended_event()
        assert list(due_feedback_events(NOW)) == [event]

    def test_event_ended_earlier_today_excluded(self, feedback_survey):
        make_ended_event(end=datetime(2026, 10, 15, 10, 0, tzinfo=TZ))
        assert not due_feedback_events(NOW).exists()

    def test_event_older_than_lookback_excluded(self, feedback_survey):
        make_ended_event(end=NOW - timedelta(days=8))
        assert not due_feedback_events(NOW).exists()

    def test_cancelled_event_excluded(self, feedback_survey):
        make_ended_event(status=EventStatus.CANCELLED)
        assert not due_feedback_events(NOW).exists()

    def test_type_without_feedback_survey_excluded(self, feedback_survey):
        make_ended_event(event_type=EventType.CLUB)
        assert not due_feedback_events(NOW).exists()

    def test_inactive_feedback_survey_excluded(self, feedback_survey):
        Survey.objects.filter(pk=feedback_survey.pk).update(is_active=False)
        make_ended_event()
        assert not due_feedback_events(NOW).exists()

    @pytest.mark.parametrize("status", [EventStatus.DRAFT, EventStatus.DELETED])
    def test_draft_and_deleted_events_excluded(self, feedback_survey, status):
        make_ended_event(status=status)
        assert not due_feedback_events(NOW).exists()

    def test_datetime_tbd_event_excluded(self, feedback_survey):
        make_ended_event(datetime_tbd=True)
        assert not due_feedback_events(NOW).exists()

    @pytest.mark.parametrize(("hours_before_cutoff", "included"), [(3, True), (1, False)])
    def test_event_without_end_uses_two_hour_default(
        self, feedback_survey, hours_before_cutoff, included
    ):
        cutoff = feedback_cutoff(NOW)
        Event.objects.create(
            title="No End",
            event_type=EventType.OFFICIAL,
            status=EventStatus.ACTIVE,
            start_datetime=cutoff - timedelta(hours=hours_before_cutoff),
        )
        assert due_feedback_events(NOW).exists() is included

    @pytest.mark.parametrize(
        ("now", "end", "included"),
        [
            (
                datetime(2026, 11, 1, 14, 0, tzinfo=TZ),
                datetime(2026, 10, 31, 23, 30, tzinfo=TZ),
                True,
            ),
            (
                datetime(2026, 11, 1, 14, 0, tzinfo=TZ),
                datetime(2026, 11, 1, 0, 30, tzinfo=TZ),
                False,
            ),
            (
                datetime(2026, 11, 2, 14, 0, tzinfo=TZ),
                datetime(2026, 11, 1, 23, 30, tzinfo=TZ),
                True,
            ),
            (
                datetime(2026, 11, 2, 14, 0, tzinfo=TZ),
                datetime(2026, 10, 26, 0, 30, tzinfo=TZ),
                True,
            ),
            (
                datetime(2026, 11, 2, 14, 0, tzinfo=TZ),
                datetime(2026, 10, 25, 23, 30, tzinfo=TZ),
                False,
            ),
        ],
    )
    def test_local_midnight_boundary_across_dst_fall_back(
        self, feedback_survey, now, end, included
    ):
        make_ended_event(end=end)
        assert due_feedback_events(now).exists() is included

    def test_feedback_url_format(self):
        assert feedback_url("abc123") == f"{settings.FRONTEND_BASE_URL}/feedback#abc123"


@pytest.mark.django_db
class TestFirstRequests:
    def test_event_ended_yesterday_emails_attended_only(self, feedback_survey, fake_email_sender):
        event = make_ended_event()
        attended = make_user()
        make_rsvp(event, attended)
        make_rsvp(event, make_user(), AttendanceStatus.DIDNT_GO)
        make_rsvp(event, make_user(), AttendanceStatus.UNKNOWN)

        assert send_first_requests(NOW)[0] == 1

        assert fake_email_sender.send.call_count == 1
        assert fake_email_sender.send.call_args.kwargs["to"] == attended.email
        request = EventFeedbackRequest.objects.get()
        assert request.user == attended
        assert request.first_sent_at == NOW

    def test_event_ended_earlier_today_not_sent(self, feedback_survey, fake_email_sender):
        event = make_ended_event(end=datetime(2026, 10, 15, 10, 0, tzinfo=TZ))
        make_rsvp(event, make_user())
        assert send_first_requests(NOW)[0] == 0
        fake_email_sender.send.assert_not_called()
        assert not EventFeedbackRequest.objects.exists()

    def test_event_older_than_lookback_not_sent(self, feedback_survey, fake_email_sender):
        event = make_ended_event(end=NOW - timedelta(days=8))
        make_rsvp(event, make_user())
        assert send_first_requests(NOW)[0] == 0
        assert not EventFeedbackRequest.objects.exists()

    def test_cancelled_event_not_sent(self, feedback_survey, fake_email_sender):
        event = make_ended_event(status=EventStatus.CANCELLED)
        make_rsvp(event, make_user())
        assert send_first_requests(NOW)[0] == 0
        assert not EventFeedbackRequest.objects.exists()

    def test_type_without_feedback_survey_not_sent(self, feedback_survey, fake_email_sender):
        event = make_ended_event(event_type=EventType.CLUB)
        make_rsvp(event, make_user())
        assert send_first_requests(NOW)[0] == 0
        assert not EventFeedbackRequest.objects.exists()

    def test_inactive_feedback_survey_not_sent(self, feedback_survey, fake_email_sender):
        Survey.objects.filter(pk=feedback_survey.pk).update(is_active=False)
        make_rsvp(make_ended_event(), make_user())
        assert send_first_requests(NOW)[0] == 0
        assert not EventFeedbackRequest.objects.exists()

    def test_rerun_same_day_sends_once(self, feedback_survey, fake_email_sender):
        make_rsvp(make_ended_event(), make_user())
        assert send_first_requests(NOW)[0] == 1
        assert send_first_requests(NOW + timedelta(hours=3))[0] == 0
        assert fake_email_sender.send.call_count == 1
        assert EventFeedbackRequest.objects.count() == 1

    def test_late_checkin_picked_up_next_run(self, feedback_survey, fake_email_sender):
        event = make_ended_event()
        early, late = make_user(), make_user()
        make_rsvp(event, early)
        late_rsvp = make_rsvp(event, late, AttendanceStatus.UNKNOWN)
        assert send_first_requests(NOW)[0] == 1

        late_rsvp.attendance = AttendanceStatus.ATTENDED
        late_rsvp.save()
        assert send_first_requests(NOW + timedelta(days=1))[0] == 1
        assert fake_email_sender.send.call_count == 2
        assert EventFeedbackRequest.objects.count() == 2

    def test_user_without_email_gets_request_but_no_send(self, feedback_survey, fake_email_sender):
        make_rsvp(make_ended_event(), make_user(email=None))
        assert send_first_requests(NOW)[0] == 0
        fake_email_sender.send.assert_not_called()
        assert EventFeedbackRequest.objects.get().first_sent_at is None

    def test_failed_send_does_not_abort_batch_and_leaves_first_sent_null(
        self, feedback_survey, fake_email_sender
    ):
        event = make_ended_event()
        first, second = make_user(), make_user()
        make_rsvp(event, first)
        make_rsvp(event, second)
        fake_email_sender.send.side_effect = [
            RuntimeError("boom"),
            SendResult(success=True, provider_message_id="ok"),
        ]
        assert send_first_requests(NOW) == (1, 1)
        assert fake_email_sender.send.call_count == 2
        assert EventFeedbackRequest.objects.filter(first_sent_at__isnull=True).count() == 1
        assert EventFeedbackRequest.objects.filter(first_sent_at__isnull=False).count() == 1

        fake_email_sender.send.side_effect = None
        fake_email_sender.send.return_value = SendResult(success=True)
        assert send_first_requests(NOW + timedelta(days=1)) == (1, 0)
        assert not EventFeedbackRequest.objects.filter(first_sent_at__isnull=True).exists()

    def test_email_contains_personal_link(self, feedback_survey, fake_email_sender):
        make_rsvp(make_ended_event(), make_user())
        send_first_requests(NOW)
        request = EventFeedbackRequest.objects.get()
        kwargs = fake_email_sender.send.call_args.kwargs
        assert feedback_url(request.token) in kwargs["html"]
        assert feedback_url(request.token) in kwargs["text"]
        assert "oct 14" in kwargs["text"]
        assert kwargs["subject"] == "how was vegan potluck?"


@pytest.mark.django_db
class TestReminders:
    def _sent_request(self, event, days_ago: int, **extra) -> EventFeedbackRequest:
        return _request(event, make_user(), first_sent_at=NOW - timedelta(days=days_ago), **extra)

    def test_reminder_after_three_days_only_to_non_responders(
        self, feedback_survey, fake_email_sender
    ):
        event = make_ended_event(end=NOW - timedelta(days=4))
        pending = self._sent_request(event, 3)
        self._sent_request(event, 3, responded_on=NOW.date())

        assert send_reminders(NOW)[0] == 1

        assert fake_email_sender.send.call_count == 1
        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == pending.user.email
        assert kwargs["subject"] == "still keen to hear about vegan potluck"
        assert feedback_url(pending.token) in kwargs["text"]
        pending.refresh_from_db()
        assert pending.reminder_sent_at == NOW

    def test_reminder_sent_once(self, feedback_survey, fake_email_sender):
        self._sent_request(make_ended_event(end=NOW - timedelta(days=4)), 3)
        assert send_reminders(NOW)[0] == 1
        assert send_reminders(NOW + timedelta(hours=6))[0] == 0
        assert send_reminders(NOW + timedelta(days=1))[0] == 0
        assert fake_email_sender.send.call_count == 1

    def test_reminder_not_sent_on_day_two(self, feedback_survey, fake_email_sender):
        self._sent_request(make_ended_event(end=NOW - timedelta(days=3)), 2)
        assert send_reminders(NOW)[0] == 0
        fake_email_sender.send.assert_not_called()

    def test_never_sent_request_gets_no_reminder(self, feedback_survey, fake_email_sender):
        _request(make_ended_event(end=NOW - timedelta(days=4)), make_user())
        assert send_reminders(NOW)[0] == 0

    def test_cancelled_event_gets_no_reminder(self, feedback_survey, fake_email_sender):
        event = make_ended_event(end=NOW - timedelta(days=4), status=EventStatus.CANCELLED)
        self._sent_request(event, 3)
        assert send_reminders(NOW)[0] == 0

    def test_reminder_not_sent_when_first_email_is_stale(self, feedback_survey, fake_email_sender):
        self._sent_request(make_ended_event(end=NOW - timedelta(days=21)), 20)
        assert send_reminders(NOW) == (0, 0)
        fake_email_sender.send.assert_not_called()

    def test_reminder_sent_at_oldest_allowed_first_email_age(
        self, feedback_survey, fake_email_sender
    ):
        self._sent_request(make_ended_event(end=NOW - timedelta(days=10)), 9)
        assert send_reminders(NOW) == (1, 0)

    def test_failed_reminder_keeps_claim(self, feedback_survey, fake_email_sender):
        request = self._sent_request(make_ended_event(end=NOW - timedelta(days=4)), 3)
        fake_email_sender.send.side_effect = RuntimeError("boom")
        assert send_reminders(NOW) == (0, 1)
        request.refresh_from_db()
        assert request.reminder_sent_at == NOW
        fake_email_sender.send.side_effect = None
        fake_email_sender.send.return_value = SendResult(success=True)
        assert send_reminders(NOW)[0] == 0


def _run_command() -> str:
    out = StringIO()
    call_command("send_event_feedback_requests", stdout=out)
    return out.getvalue().strip()


@pytest.mark.django_db
def test_command_runs_both_passes_once_per_day(feedback_survey, fake_email_sender):
    old = make_ended_event(end=datetime.now(TZ) - timedelta(days=5))
    due_reminder = _request(old, make_user(), first_sent_at=datetime.now(TZ) - timedelta(days=3))
    fresh = make_ended_event(end=datetime.now(TZ) - timedelta(days=1) - timedelta(hours=1))
    make_rsvp(fresh, make_user())

    assert _run_command() == "Sent 1 feedback request(s); 1 reminder(s)."

    due_reminder.refresh_from_db()
    assert due_reminder.reminder_sent_at is not None
    assert EventFeedbackRequest.objects.get(event=fresh).first_sent_at is not None
    assert fake_email_sender.send.call_count == 2

    assert _run_command() == "Sent 0 feedback request(s); 0 reminder(s)."
    assert fake_email_sender.send.call_count == 2


@pytest.mark.django_db
def test_command_reports_failed_sends(feedback_survey, fake_email_sender):
    make_rsvp(make_ended_event(end=datetime.now(TZ) - timedelta(days=1, hours=1)), make_user())
    fake_email_sender.send.side_effect = RuntimeError("boom")

    assert _run_command() == "Sent 0 feedback request(s); 0 reminder(s). 1 failed."
