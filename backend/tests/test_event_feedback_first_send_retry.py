from datetime import datetime, timedelta

import pytest
from community._event_feedback_send import send_first_requests
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
from django.utils import timezone
from notifications.email_sender import SendResult
from users.models import User

TZ = settings.COMMUNITY_TZ
NOW = datetime(2026, 10, 15, 14, 0, tzinfo=TZ)
OK = SendResult(success=True, provider_message_id="ok")

pytestmark = pytest.mark.django_db


@pytest.fixture
def event(db):
    Survey.objects.create(
        title="official feedback", slug="official-feedback", feedback_event_type=EventType.OFFICIAL
    )
    end = datetime(2026, 10, 14, 20, 0, tzinfo=TZ)
    return Event.objects.create(
        title="Vegan Potluck",
        event_type=EventType.OFFICIAL,
        status=EventStatus.ACTIVE,
        start_datetime=end - timedelta(hours=2),
        end_datetime=end,
    )


def _attendee(event: Event, n: int, **user_extra) -> User:
    user = User.objects.create_user(
        phone_number=f"+1202555{n:04d}",
        password="testpass123",
        first_name="Sam",
        email=f"retry{n}@example.test",
        **user_extra,
    )
    EventRSVP.objects.create(
        event=event, user=user, status=RSVPStatus.ATTENDING, attendance=AttendanceStatus.ATTENDED
    )
    return user


@pytest.mark.parametrize("failure", [RuntimeError("boom"), SendResult(success=False, error="x")])
def test_failed_send_is_retried_on_next_run(event, fake_email_sender, failure):
    _attendee(event, 1)
    fake_email_sender.send.side_effect = [failure, OK]

    assert send_first_requests(NOW) == 0
    assert EventFeedbackRequest.objects.get().first_sent_at is None

    later = NOW + timedelta(days=1)
    assert send_first_requests(later) == 1
    assert EventFeedbackRequest.objects.get().first_sent_at == later


def test_failure_does_not_block_rest_of_batch(event, fake_email_sender):
    _attendee(event, 1)
    _attendee(event, 2)
    fake_email_sender.send.side_effect = [RuntimeError("boom"), OK]

    assert send_first_requests(NOW) == 1
    assert EventFeedbackRequest.objects.filter(first_sent_at__isnull=True).count() == 1


def test_overlapping_run_cannot_double_send(event, fake_email_sender):
    _attendee(event, 1)
    inner_sent: list[int] = []

    def send_while_other_run_in_flight(**kwargs):
        if not inner_sent:
            inner_sent.append(send_first_requests(NOW))
        return OK

    fake_email_sender.send.side_effect = send_while_other_run_in_flight

    assert send_first_requests(NOW) == 1
    assert inner_sent == [0]
    assert fake_email_sender.send.call_count == 1


def test_user_without_email_is_never_attempted(event, fake_email_sender):
    user = _attendee(event, 1)
    User.objects.filter(pk=user.pk).update(email="")

    assert send_first_requests(NOW) == 0
    assert send_first_requests(NOW + timedelta(days=1)) == 0
    fake_email_sender.send.assert_not_called()
    assert EventFeedbackRequest.objects.get().first_sent_at is None


@pytest.mark.parametrize("extra", [{"is_active": False}, {"archived_at": timezone.now()}])
def test_archived_or_inactive_attendee_not_emailed(event, fake_email_sender, extra):
    _attendee(event, 1, **extra)
    assert send_first_requests(NOW) == 0
    fake_email_sender.send.assert_not_called()
    assert not EventFeedbackRequest.objects.exists()
