from datetime import datetime, timedelta

import pytest
from community._event_feedback_send import (
    due_feedback_events,
    feedback_url,
    send_first_requests,
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
