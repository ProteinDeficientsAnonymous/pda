from datetime import timedelta
from decimal import Decimal

import pytest
from community.models import EventRSVP, RSVPStatus
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
from users.models import NonMemberRsvpToken, User

from tests._public_rsvp_helpers import make_non_member, make_official_event, post

LOCATION = "18 Willow House, Apt 4"
LATITUDE = "40.712776"
LONGITUDE = "-74.005974"
EMAIL_TEMPLATES = sorted((settings.BASE_DIR / "templates" / "emails").iterdir())


@pytest.fixture
def located_event(db):
    return make_official_event(
        title="Loft Potluck",
        location=LOCATION,
        latitude=Decimal(LATITUDE),
        longitude=Decimal(LONGITUDE),
    )


def _assert_no_location(sent: dict) -> None:
    for part in ("subject", "html", "text"):
        body = sent[part].lower()
        assert LOCATION.lower() not in body
        assert "willow" not in body
        assert LATITUDE not in body
        assert LONGITUDE not in body


def _assert_no_where_line(sent: dict) -> None:
    assert "where:" not in sent["html"].lower()
    assert "where:" not in sent["text"].lower()


def _sent_with_subject(fake_email_sender, fragment: str) -> dict:
    matches = [
        c.kwargs for c in fake_email_sender.send.call_args_list if fragment in c.kwargs["subject"]
    ]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.django_db
class TestRsvpEmailsOmitLocation:
    def test_confirmation(self, api_client, located_event, fake_email_sender):
        assert post(api_client, located_event).status_code == 200

        sent = _sent_with_subject(fake_email_sender, "you're in for")
        _assert_no_location(sent)
        _assert_no_where_line(sent)

    def test_updated(self, api_client, located_event, fake_email_sender):
        nonmember = make_non_member("+14155550031", "nm@example.com", name="non member")
        EventRSVP.objects.create(event=located_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)

        resp = api_client.post(
            f"/api/community/public/my-rsvps/{located_event.id}/?token={token.token}",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )

        assert resp.status_code == 200
        sent = _sent_with_subject(fake_email_sender, "your rsvp was updated")
        _assert_no_location(sent)
        _assert_no_where_line(sent)

    def test_waitlist_promoted(self, api_client, auth_headers, located_event, fake_email_sender):
        located_event.max_attendees = 1
        located_event.save(update_fields=["max_attendees"])
        rsvp_url = f"/api/community/events/{located_event.id}/rsvp/"
        api_client.post(
            rsvp_url,
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        waited = make_non_member("+14155550032", "waited@example.com", name="Waited")
        EventRSVP.objects.create(event=located_event, user=waited, status=RSVPStatus.WAITLISTED)

        api_client.delete(rsvp_url, **auth_headers)

        sent = _sent_with_subject(fake_email_sender, "off the waitlist")
        _assert_no_location(sent)
        _assert_no_where_line(sent)


@pytest.mark.django_db
def test_weekly_digest_omits_location(fake_email_sender):
    User.objects.create_user(
        phone_number="+12025550301",
        password="testpass123",
        email="digest@example.com",
        first_name="Test",
        is_member=True,
    )
    event = make_official_event(
        title="Loft Potluck",
        start_datetime=timezone.now() + timedelta(days=2),
        location=LOCATION,
        latitude=Decimal(LATITUDE),
        longitude=Decimal(LONGITUDE),
    )

    call_command("send_weekly_digest")

    sent = _sent_with_subject(fake_email_sender, "coming up this week")
    _assert_no_location(sent)
    assert f"{settings.FRONTEND_BASE_URL}/events/{event.slug or event.pk}" in sent["text"]


@pytest.mark.parametrize("template", EMAIL_TEMPLATES, ids=lambda p: p.name)
def test_email_templates_never_reference_location(template):
    source = template.read_text().lower()
    for field in ("location", "latitude", "longitude"):
        assert field not in source
