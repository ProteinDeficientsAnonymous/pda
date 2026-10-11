import pytest
from community.models import Event, EventRSVP, RSVPStatus
from django.test import Client
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso


def _member(phone="+14155550100", email="member@e.com"):
    return User.objects.create_user(
        phone_number=phone, password="p", email=email, first_name="Mem", last_name="Ber"
    )


def _headers(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}


def _event(creator, **kwargs):
    return Event.objects.create(
        title="Picnic",
        start_datetime=future_iso(days=30),
        rsvp_enabled=True,
        location="the park",
        created_by=creator,
        **kwargs,
    )


def _rsvp(client, event, user, status, has_plus_one=False):
    return client.post(
        f"/api/community/events/{event.id}/rsvp/",
        {"status": status, "has_plus_one": has_plus_one},
        content_type="application/json",
        **_headers(user),
    )


def _subjects(fake, to):
    return [c.kwargs["subject"] for c in fake.send.call_args_list if c.kwargs["to"] == to]


@pytest.mark.django_db
class TestMemberRsvpStatusEmail:
    @pytest.mark.parametrize(
        ("status", "subject"),
        [
            (RSVPStatus.ATTENDING, "you're in for picnic"),
            (RSVPStatus.MAYBE, "you're a maybe for picnic"),
            (RSVPStatus.CANT_GO, "you're not going to picnic"),
        ],
    )
    def test_first_rsvp_emails_member(self, test_user, fake_email_sender, status, subject):
        member = _member()
        event = _event(test_user)

        assert _rsvp(Client(), event, member, status).status_code == 200

        assert _subjects(fake_email_sender, "member@e.com") == [subject]
        sent = fake_email_sender.send.call_args.kwargs
        assert f"/events/{event.slug or event.id}" in sent["text"]

    def test_status_change_emails_member(self, test_user, fake_email_sender):
        member = _member()
        event = _event(test_user)
        client = Client()
        _rsvp(client, event, member, RSVPStatus.ATTENDING)
        _rsvp(client, event, member, RSVPStatus.CANT_GO)

        assert _subjects(fake_email_sender, "member@e.com") == [
            "you're in for picnic",
            "you're not going to picnic",
        ]

    def test_resave_same_status_does_not_email(self, test_user, fake_email_sender):
        member = _member()
        event = _event(test_user, allow_plus_ones=True)
        client = Client()
        _rsvp(client, event, member, RSVPStatus.ATTENDING)
        _rsvp(client, event, member, RSVPStatus.ATTENDING, has_plus_one=True)

        assert _subjects(fake_email_sender, "member@e.com") == ["you're in for picnic"]

    def test_at_capacity_emails_waitlisted(self, test_user, fake_email_sender):
        member = _member()
        event = _event(test_user, max_attendees=1)
        EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)

        _rsvp(Client(), event, member, RSVPStatus.ATTENDING)

        assert _subjects(fake_email_sender, "member@e.com") == ["you're on the waitlist for picnic"]

    def test_member_without_email_is_skipped(self, test_user, fake_email_sender):
        member = _member(email=None)
        event = _event(test_user)

        assert _rsvp(Client(), event, member, RSVPStatus.ATTENDING).status_code == 200

        fake_email_sender.send.assert_not_called()

    def test_send_failure_does_not_fail_rsvp(self, test_user, fake_email_sender):
        fake_email_sender.send.side_effect = RuntimeError("boom")
        member = _member()
        event = _event(test_user)

        assert _rsvp(Client(), event, member, RSVPStatus.ATTENDING).status_code == 200
        assert EventRSVP.objects.get(event=event, user=member).status == RSVPStatus.ATTENDING

    def test_cant_go_email_omits_location(self, test_user, fake_email_sender):
        member = _member()
        event = _event(test_user)

        _rsvp(Client(), event, member, RSVPStatus.CANT_GO)

        assert "the park" not in fake_email_sender.send.call_args.kwargs["text"]


@pytest.mark.django_db
class TestMemberWaitlistPromotionEmail:
    def test_promoted_member_gets_event_link_not_manage_link(self, test_user, fake_email_sender):
        event = _event(test_user, max_attendees=1)
        EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)
        member = _member()
        EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.WAITLISTED)

        _rsvp(Client(), event, test_user, RSVPStatus.CANT_GO)

        promoted = [
            c.kwargs
            for c in fake_email_sender.send.call_args_list
            if c.kwargs["to"] == "member@e.com"
        ]
        assert [p["subject"] for p in promoted] == ["you're off the waitlist for picnic"]
        assert f"/events/{event.slug or event.id}" in promoted[0]["text"]
        assert "my-rsvps?token=" not in promoted[0]["text"]
