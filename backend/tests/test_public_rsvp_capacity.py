import logging

import pytest
from community.models import EventRSVP, RSVPStatus
from notifications.email_sender import SendResult
from users.models import NonMemberRsvpToken, User

from tests._public_rsvp_helpers import make_non_member, make_official_event, post


def _capped_event(max_attendees=1):
    return make_official_event(
        title="Capped Official", allow_plus_ones=True, max_attendees=max_attendees
    )


@pytest.mark.django_db
class TestPublicRsvpCapacity:
    def test_at_cap_auto_waitlists(self, api_client, fake_email_sender):
        event = _capped_event(max_attendees=1)
        first = post(api_client, event, phone_number="+14155550101", email="a@e.com")
        assert first.json()["rsvp"]["status"] == RSVPStatus.ATTENDING

        second = post(api_client, event, phone_number="+14155550102", email="b@e.com")
        assert second.status_code == 200
        assert second.json()["rsvp"]["status"] == RSVPStatus.WAITLISTED
        # Confirmation email reflects the waitlist.
        assert "waitlist" in fake_email_sender.send.call_args.kwargs["subject"]

    def test_plus_one_at_cap_auto_waitlists(self, api_client, fake_email_sender):
        event = _capped_event(max_attendees=1)
        post(api_client, event, phone_number="+14155550101", email="a@e.com")
        # A new attendee with a +1 at cap is auto-waitlisted (not a 400). The 400
        # NO_PLUS_ONE_SPOTS only fires for an already-attending toggler.
        response = post(
            api_client,
            event,
            phone_number="+14155550102",
            email="b@e.com",
            has_plus_one=True,
        )
        assert response.status_code == 200
        assert response.json()["rsvp"]["status"] == RSVPStatus.WAITLISTED

    def test_spot_freed_promotes_and_emails_non_member(self, api_client, fake_email_sender):
        event = _capped_event(max_attendees=1)
        attendee = make_non_member("+14155550101", "a@e.com")
        EventRSVP.objects.create(event=event, user=attendee, status=RSVPStatus.ATTENDING)
        waited = make_non_member("+14155550102", "b@e.com", name="Waited")
        EventRSVP.objects.create(event=event, user=waited, status=RSVPStatus.WAITLISTED)

        # Attendee changes to can't-go via the public endpoint → frees the spot.
        response = post(
            api_client,
            event,
            name="A",
            phone_number="+14155550101",
            email="a@e.com",
            status=RSVPStatus.CANT_GO,
        )
        assert response.status_code == 200

        waited.refresh_from_db()
        promoted_rsvp = EventRSVP.objects.get(event=event, user=waited)
        assert promoted_rsvp.status == RSVPStatus.ATTENDING
        # Promoted non-member was emailed a fresh manage link.
        promoted_emails = [
            c
            for c in fake_email_sender.send.call_args_list
            if c.kwargs["to"] == "b@e.com" and "off the waitlist" in c.kwargs["subject"]
        ]
        assert len(promoted_emails) == 1
        assert NonMemberRsvpToken.objects.filter(user=waited).exists()


def _capture_audit(caplog):
    """Attach caplog's handler to the non-propagating pda.audit logger.

    pda.audit has propagate=False (see settings LOGGING), so caplog's root
    handler never sees its records. Attaching the handler directly captures them.
    """
    audit_logger = logging.getLogger("pda.audit")
    audit_logger.addHandler(caplog.handler)
    return audit_logger


@pytest.fixture
def official_event(db):
    return make_official_event()


@pytest.mark.django_db
class TestPublicRsvpRobustness:
    def test_audit_log_written(self, api_client, official_event, fake_email_sender, caplog):
        audit_logger = _capture_audit(caplog)
        try:
            with caplog.at_level(logging.INFO, logger="pda.audit"):
                post(api_client, official_event)
        finally:
            audit_logger.removeHandler(caplog.handler)

        user = User.objects.get(phone_number="+14155550123")
        records = [r for r in caplog.records if getattr(r, "action", None) == "public_rsvp_created"]
        assert len(records) == 1
        assert records[0].target_id == str(official_event.id)
        assert records[0].details["user_id"] == str(user.pk)

    def test_email_failure_does_not_roll_back_rsvp(
        self, api_client, official_event, fake_email_sender, caplog
    ):
        fake_email_sender.send.return_value = SendResult(success=False, error="boom")

        audit_logger = _capture_audit(caplog)
        try:
            with caplog.at_level(logging.WARNING, logger="pda.audit"):
                response = post(api_client, official_event)
        finally:
            audit_logger.removeHandler(caplog.handler)

        assert response.status_code == 200
        user = User.objects.get(phone_number="+14155550123")
        assert EventRSVP.objects.filter(event=official_event, user=user).exists()
        assert NonMemberRsvpToken.objects.filter(user=user).exists()
        failures = [
            r for r in caplog.records if getattr(r, "action", None) == "public_rsvp_email_failed"
        ]
        assert len(failures) == 1
