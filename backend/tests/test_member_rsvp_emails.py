import pytest
from community.models import Event, EventRSVP, RSVPStatus
from django.test import Client
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests._public_rsvp_helpers import make_non_member, make_tentative_member
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
    def test_going_emails_member(self, test_user, fake_email_sender):
        member = _member()
        event = _event(test_user)

        assert _rsvp(Client(), event, member, RSVPStatus.ATTENDING).status_code == 200

        assert _subjects(fake_email_sender, "member@e.com") == ["you're in for picnic"]
        sent = fake_email_sender.send.call_args.kwargs
        assert f"/events/{event.slug or event.id}" in sent["text"]

    @pytest.mark.parametrize("status", [RSVPStatus.MAYBE, RSVPStatus.CANT_GO])
    def test_maybe_or_cant_go_does_not_email(self, test_user, fake_email_sender, status):
        member = _member()
        event = _event(test_user)
        client = Client()
        _rsvp(client, event, member, RSVPStatus.ATTENDING)
        _rsvp(client, event, member, status)

        assert _subjects(fake_email_sender, "member@e.com") == ["you're in for picnic"]

    def test_resave_same_status_does_not_email(self, test_user, fake_email_sender):
        member = _member()
        event = _event(test_user, allow_plus_ones=True)
        client = Client()
        _rsvp(client, event, member, RSVPStatus.ATTENDING)
        _rsvp(client, event, member, RSVPStatus.ATTENDING, has_plus_one=True)

        assert _subjects(fake_email_sender, "member@e.com") == ["you're in for picnic"]

    def test_landing_on_waitlist_does_not_email(self, test_user, fake_email_sender):
        member = _member()
        event = _event(test_user, max_attendees=1)
        EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)

        _rsvp(Client(), event, member, RSVPStatus.ATTENDING)

        assert EventRSVP.objects.get(event=event, user=member).status == RSVPStatus.WAITLISTED
        assert _subjects(fake_email_sender, "member@e.com") == []

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

    def test_promoted_unpaid_member_is_told_to_pay(self, test_user, fake_email_sender):
        event = _event(
            test_user, max_attendees=1, price="$10", venmo_link="https://venmo.com/u/host"
        )
        EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)
        member = _member()
        EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.WAITLISTED)

        _rsvp(Client(), event, test_user, RSVPStatus.CANT_GO)

        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == "member@e.com"
        assert "your spot isn't confirmed until you pay" in sent["text"]

    def test_capacity_increase_emails_promoted_member(self, test_user, fake_email_sender):
        event = _event(test_user, max_attendees=1)
        EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)
        member = _member()
        EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.WAITLISTED)

        Client().patch(
            f"/api/community/events/{event.id}/",
            {"max_attendees": 2},
            content_type="application/json",
            **_headers(test_user),
        )

        assert EventRSVP.objects.get(event=event, user=member).status == RSVPStatus.ATTENDING
        assert _subjects(fake_email_sender, "member@e.com") == [
            "you're off the waitlist for picnic"
        ]


def _host_set(event, host, guest, status):
    return Client().post(
        f"/api/community/events/{event.id}/rsvps/{guest.pk}/rsvp/",
        {"status": status},
        content_type="application/json",
        **_headers(host),
    )


@pytest.mark.django_db
class TestHostSetRsvpEmail:
    def test_host_seating_waitlisted_member_emails_them(self, test_user, fake_email_sender):
        event = _event(test_user)
        member = _member()
        EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.WAITLISTED)

        assert _host_set(event, test_user, member, RSVPStatus.ATTENDING).status_code == 200

        assert _subjects(fake_email_sender, "member@e.com") == ["you're in for picnic"]

    def test_host_setting_cant_go_does_not_email(self, test_user, fake_email_sender):
        event = _event(test_user)
        member = _member()
        EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.ATTENDING)

        _host_set(event, test_user, member, RSVPStatus.CANT_GO)

        assert _subjects(fake_email_sender, "member@e.com") == []

    def test_host_resave_same_status_does_not_email(self, test_user, fake_email_sender):
        event = _event(test_user)
        member = _member()
        EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.ATTENDING)

        _host_set(event, test_user, member, RSVPStatus.ATTENDING)

        assert _subjects(fake_email_sender, "member@e.com") == []

    def test_host_set_tentative_member_gets_member_email(self, test_user, fake_email_sender):
        event = _event(test_user)
        tentative = make_tentative_member("+14155550101", "tentative@e.com")

        _host_set(event, test_user, tentative, RSVPStatus.ATTENDING)

        assert _subjects(fake_email_sender, "tentative@e.com") == ["you're in for picnic"]

    def test_host_set_public_rsvper_gets_no_member_email(self, test_user, fake_email_sender):
        event = _event(test_user)
        non_member = make_non_member("+14155550102", "public@e.com")

        _host_set(event, test_user, non_member, RSVPStatus.ATTENDING)

        assert _subjects(fake_email_sender, "public@e.com") == []


@pytest.mark.django_db
def test_text_part_is_not_html_escaped(test_user, fake_email_sender):
    member = _member()
    event = _event(test_user)
    event.title = "Leah's Potluck & Games"
    event.location = "Joe's Place"
    event.save()

    _rsvp(Client(), event, member, RSVPStatus.ATTENDING)

    text = fake_email_sender.send.call_args.kwargs["text"]
    assert "leah's potluck & games" in text
    assert "joe's place" in text
