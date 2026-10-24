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
    EventRSVP,
    EventStatus,
    EventType,
    RSVPStatus,
    Survey,
)
from django.conf import settings
from django.core.management import call_command
from notifications.email_sender import SendResult
from users.models import User

TZ = settings.COMMUNITY_TZ
NOW = datetime(2026, 10, 15, 14, 0, tzinfo=TZ)
YESTERDAY_EVENING = datetime(2026, 10, 14, 20, 0, tzinfo=TZ)


@pytest.fixture
def feedback_survey(db):
    return Survey.objects.create(
        title="official feedback", slug="official-feedback", feedback_event_type=EventType.OFFICIAL
    )


def _event(*, end=YESTERDAY_EVENING, event_type=EventType.OFFICIAL, **extra) -> Event:
    return Event.objects.create(
        title="Vegan Potluck",
        event_type=event_type,
        status=extra.pop("status", EventStatus.ACTIVE),
        start_datetime=end - timedelta(hours=2),
        end_datetime=end,
        **extra,
    )


_phone_counter = iter(range(1000, 9999))


def _user(email: str | None = "auto") -> User:
    n = next(_phone_counter)
    return User.objects.create_user(
        phone_number=f"+1202555{n}",
        password="testpass123",
        first_name="Sam",
        email=f"u{n}@example.test" if email == "auto" else email,
    )


def _rsvp(event: Event, user: User, attendance=AttendanceStatus.ATTENDED) -> EventRSVP:
    return EventRSVP.objects.create(
        event=event, user=user, status=RSVPStatus.ATTENDING, attendance=attendance
    )


def _request(event, user, **extra) -> EventFeedbackRequest:
    return EventFeedbackRequest.objects.create(
        event=event, user=user, token=EventFeedbackRequest.new_token(), **extra
    )


@pytest.mark.django_db
class TestDueFeedbackEvents:
    def test_event_ended_yesterday_included(self, feedback_survey):
        event = _event()
        assert list(due_feedback_events(NOW)) == [event]

    def test_event_ended_earlier_today_excluded(self, feedback_survey):
        _event(end=datetime(2026, 10, 15, 10, 0, tzinfo=TZ))
        assert not due_feedback_events(NOW).exists()

    def test_event_older_than_lookback_excluded(self, feedback_survey):
        _event(end=NOW - timedelta(days=8))
        assert not due_feedback_events(NOW).exists()

    def test_cancelled_event_excluded(self, feedback_survey):
        _event(status=EventStatus.CANCELLED)
        assert not due_feedback_events(NOW).exists()

    def test_type_without_feedback_survey_excluded(self, feedback_survey):
        _event(event_type=EventType.CLUB)
        assert not due_feedback_events(NOW).exists()

    def test_inactive_feedback_survey_excluded(self, feedback_survey):
        Survey.objects.filter(pk=feedback_survey.pk).update(is_active=False)
        _event()
        assert not due_feedback_events(NOW).exists()

    @pytest.mark.parametrize("status", [EventStatus.DRAFT, EventStatus.DELETED])
    def test_draft_and_deleted_events_excluded(self, feedback_survey, status):
        _event(status=status)
        assert not due_feedback_events(NOW).exists()

    def test_datetime_tbd_event_excluded(self, feedback_survey):
        _event(datetime_tbd=True)
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
        _event(end=end)
        assert due_feedback_events(now).exists() is included

    def test_feedback_url_format(self):
        assert feedback_url("abc123") == f"{settings.FRONTEND_BASE_URL}/feedback/abc123"


@pytest.mark.django_db
class TestFirstRequests:
    def test_event_ended_yesterday_emails_attended_only(self, feedback_survey, fake_email_sender):
        event = _event()
        attended = _user()
        _rsvp(event, attended)
        _rsvp(event, _user(), AttendanceStatus.DIDNT_GO)
        _rsvp(event, _user(), AttendanceStatus.UNKNOWN)

        assert send_first_requests(NOW) == 1

        assert fake_email_sender.send.call_count == 1
        assert fake_email_sender.send.call_args.kwargs["to"] == attended.email
        request = EventFeedbackRequest.objects.get()
        assert request.user == attended
        assert request.first_sent_at == NOW

    def test_event_ended_earlier_today_not_sent(self, feedback_survey, fake_email_sender):
        event = _event(end=datetime(2026, 10, 15, 10, 0, tzinfo=TZ))
        _rsvp(event, _user())
        assert send_first_requests(NOW) == 0
        fake_email_sender.send.assert_not_called()
        assert not EventFeedbackRequest.objects.exists()

    def test_event_older_than_lookback_not_sent(self, feedback_survey, fake_email_sender):
        event = _event(end=NOW - timedelta(days=8))
        _rsvp(event, _user())
        assert send_first_requests(NOW) == 0
        assert not EventFeedbackRequest.objects.exists()

    def test_cancelled_event_not_sent(self, feedback_survey, fake_email_sender):
        event = _event(status=EventStatus.CANCELLED)
        _rsvp(event, _user())
        assert send_first_requests(NOW) == 0
        assert not EventFeedbackRequest.objects.exists()

    def test_type_without_feedback_survey_not_sent(self, feedback_survey, fake_email_sender):
        event = _event(event_type=EventType.CLUB)
        _rsvp(event, _user())
        assert send_first_requests(NOW) == 0
        assert not EventFeedbackRequest.objects.exists()

    def test_inactive_feedback_survey_not_sent(self, feedback_survey, fake_email_sender):
        Survey.objects.filter(pk=feedback_survey.pk).update(is_active=False)
        _rsvp(_event(), _user())
        assert send_first_requests(NOW) == 0
        assert not EventFeedbackRequest.objects.exists()

    def test_rerun_same_day_sends_once(self, feedback_survey, fake_email_sender):
        _rsvp(_event(), _user())
        assert send_first_requests(NOW) == 1
        assert send_first_requests(NOW + timedelta(hours=3)) == 0
        assert fake_email_sender.send.call_count == 1
        assert EventFeedbackRequest.objects.count() == 1

    def test_late_checkin_picked_up_next_run(self, feedback_survey, fake_email_sender):
        event = _event()
        early, late = _user(), _user()
        _rsvp(event, early)
        late_rsvp = _rsvp(event, late, AttendanceStatus.UNKNOWN)
        assert send_first_requests(NOW) == 1

        late_rsvp.attendance = AttendanceStatus.ATTENDED
        late_rsvp.save()
        assert send_first_requests(NOW + timedelta(days=1)) == 1
        assert fake_email_sender.send.call_count == 2
        assert EventFeedbackRequest.objects.count() == 2

    def test_user_without_email_gets_request_but_no_send(self, feedback_survey, fake_email_sender):
        _rsvp(_event(), _user(email=None))
        assert send_first_requests(NOW) == 0
        fake_email_sender.send.assert_not_called()
        assert EventFeedbackRequest.objects.get().first_sent_at is None

    def test_failed_send_does_not_abort_batch_and_leaves_first_sent_null(
        self, feedback_survey, fake_email_sender
    ):
        event = _event()
        first, second = _user(), _user()
        _rsvp(event, first)
        _rsvp(event, second)
        fake_email_sender.send.side_effect = [
            RuntimeError("boom"),
            SendResult(success=True, provider_message_id="ok"),
        ]
        assert send_first_requests(NOW) == 1
        assert fake_email_sender.send.call_count == 2
        assert EventFeedbackRequest.objects.filter(first_sent_at__isnull=True).count() == 1
        assert EventFeedbackRequest.objects.filter(first_sent_at__isnull=False).count() == 1

    def test_email_contains_personal_link(self, feedback_survey, fake_email_sender):
        _rsvp(_event(), _user())
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
        return _request(event, _user(), first_sent_at=NOW - timedelta(days=days_ago), **extra)

    def test_reminder_after_three_days_only_to_non_responders(
        self, feedback_survey, fake_email_sender
    ):
        event = _event(end=NOW - timedelta(days=4))
        pending = self._sent_request(event, 3)
        self._sent_request(event, 3, responded_on=NOW.date())

        assert send_reminders(NOW) == 1

        assert fake_email_sender.send.call_count == 1
        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == pending.user.email
        assert kwargs["subject"] == "still keen to hear about vegan potluck"
        assert feedback_url(pending.token) in kwargs["text"]
        pending.refresh_from_db()
        assert pending.reminder_sent_at == NOW

    def test_reminder_sent_once(self, feedback_survey, fake_email_sender):
        self._sent_request(_event(end=NOW - timedelta(days=4)), 3)
        assert send_reminders(NOW) == 1
        assert send_reminders(NOW + timedelta(hours=6)) == 0
        assert send_reminders(NOW + timedelta(days=1)) == 0
        assert fake_email_sender.send.call_count == 1

    def test_reminder_not_sent_on_day_two(self, feedback_survey, fake_email_sender):
        self._sent_request(_event(end=NOW - timedelta(days=3)), 2)
        assert send_reminders(NOW) == 0
        fake_email_sender.send.assert_not_called()

    def test_never_sent_request_gets_no_reminder(self, feedback_survey, fake_email_sender):
        _request(_event(end=NOW - timedelta(days=4)), _user())
        assert send_reminders(NOW) == 0

    def test_cancelled_event_gets_no_reminder(self, feedback_survey, fake_email_sender):
        event = _event(end=NOW - timedelta(days=4), status=EventStatus.CANCELLED)
        self._sent_request(event, 3)
        assert send_reminders(NOW) == 0

    def test_failed_reminder_keeps_claim(self, feedback_survey, fake_email_sender):
        request = self._sent_request(_event(end=NOW - timedelta(days=4)), 3)
        fake_email_sender.send.side_effect = RuntimeError("boom")
        assert send_reminders(NOW) == 0
        request.refresh_from_db()
        assert request.reminder_sent_at == NOW
        fake_email_sender.send.side_effect = None
        fake_email_sender.send.return_value = SendResult(success=True)
        assert send_reminders(NOW) == 0


@pytest.mark.django_db
def test_command_runs_both_passes(feedback_survey, fake_email_sender):
    old = _event(end=datetime.now(TZ) - timedelta(days=5))
    due_reminder = _request(old, _user(), first_sent_at=datetime.now(TZ) - timedelta(days=3))
    fresh = _event(end=datetime.now(TZ) - timedelta(days=1) - timedelta(hours=1))
    _rsvp(fresh, _user())
    out = StringIO()

    call_command("send_event_feedback_requests", stdout=out)

    due_reminder.refresh_from_db()
    assert due_reminder.reminder_sent_at is not None
    assert fake_email_sender.send.call_count >= 1
    assert "request" in out.getvalue()
