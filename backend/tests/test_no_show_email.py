from datetime import datetime, timedelta
from io import StringIO

import pytest
from community.attendance.no_show_email import send_no_show_emails
from community.models import AttendanceStatus, EventRSVP, EventStatus, EventType
from django.core.management import call_command
from django.utils import timezone
from notifications.email_sender import SendResult

from tests._event_feedback_helpers import NOW, TZ, make_ended_event, make_rsvp
from tests._users import make_user


def _no_show(event=None, **user_fields) -> EventRSVP:
    return make_rsvp(
        event or make_ended_event(), make_user(**user_fields), AttendanceStatus.DIDNT_GO
    )


@pytest.mark.django_db
class TestSendNoShowEmails:
    def test_didnt_go_gets_one_email(self, fake_email_sender):
        rsvp = _no_show()
        assert send_no_show_emails(NOW) == (1, 0)
        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == rsvp.user.email
        assert "vegan potluck" in kwargs["subject"]
        rsvp.refresh_from_db()
        assert rsvp.no_show_emailed_at == NOW

    @pytest.mark.parametrize("attendance", [AttendanceStatus.ATTENDED, AttendanceStatus.UNKNOWN])
    def test_attended_and_unknown_get_nothing(self, fake_email_sender, attendance):
        make_rsvp(make_ended_event(), make_user(), attendance)
        assert send_no_show_emails(NOW) == (0, 0)
        fake_email_sender.send.assert_not_called()

    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_official_and_club_events_send(self, fake_email_sender, event_type):
        _no_show(make_ended_event(event_type=event_type))
        assert send_no_show_emails(NOW) == (1, 0)

    def test_community_event_never_sends(self, fake_email_sender):
        _no_show(make_ended_event(event_type=EventType.COMMUNITY))
        assert send_no_show_emails(NOW) == (0, 0)

    def test_rerun_sends_once(self, fake_email_sender):
        _no_show()
        send_no_show_emails(NOW)
        send_no_show_emails(NOW + timedelta(days=1))
        assert fake_email_sender.send.call_count == 1

    def test_event_ended_earlier_today_waits(self, fake_email_sender):
        _no_show(make_ended_event(end=datetime(2026, 10, 15, 10, 0, tzinfo=TZ)))
        assert send_no_show_emails(NOW) == (0, 0)

    def test_event_older_than_lookback_skipped(self, fake_email_sender):
        _no_show(make_ended_event(end=NOW - timedelta(days=8)))
        assert send_no_show_emails(NOW) == (0, 0)

    def test_late_mark_picked_up_next_run(self, fake_email_sender):
        event = make_ended_event()
        rsvp = make_rsvp(event, make_user(), AttendanceStatus.UNKNOWN)
        send_no_show_emails(NOW)
        EventRSVP.objects.filter(pk=rsvp.pk).update(attendance=AttendanceStatus.DIDNT_GO)
        assert send_no_show_emails(NOW + timedelta(days=1)) == (1, 0)

    def test_cancelled_event_skipped(self, fake_email_sender):
        _no_show(make_ended_event(status=EventStatus.CANCELLED))
        assert send_no_show_emails(NOW) == (0, 0)

    def test_archived_member_skipped(self, fake_email_sender):
        _no_show(archived_at=timezone.now())
        assert send_no_show_emails(NOW) == (0, 0)

    def test_member_without_email_skipped(self, fake_email_sender):
        _no_show(email="")
        assert send_no_show_emails(NOW) == (0, 0)
        fake_email_sender.send.assert_not_called()

    def test_failed_send_releases_claim_for_retry(self, fake_email_sender):
        rsvp = _no_show()
        fake_email_sender.send.return_value = SendResult(success=False, error="boom")
        assert send_no_show_emails(NOW) == (0, 1)
        rsvp.refresh_from_db()
        assert rsvp.no_show_emailed_at is None

    def test_exception_does_not_abort_batch(self, fake_email_sender):
        event = make_ended_event()
        _no_show(event)
        _no_show(event)
        fake_email_sender.send.side_effect = [RuntimeError("boom"), SendResult(success=True)]
        assert send_no_show_emails(NOW) == (1, 1)

    def test_command_reports_counts(self, fake_email_sender):
        _no_show(make_ended_event(end=timezone.now() - timedelta(days=2)))
        out = StringIO()
        call_command("send_no_show_emails", stdout=out)
        assert "Sent 1 no-show email(s)." in out.getvalue()
