"""Tests for the public "resend my manage link" recovery endpoint.

POST /api/community/public/my-rsvps/resend/ — no auth. Given a phone, re-sends a
non-member's scoped manage link (to the on-file email) so they can recover access
without re-submitting an RSVP. Always returns the same neutral 200 (no enumeration).
"""

import pytest
from community.rsvps.public_resend import NEUTRAL_RESPONSE
from community.validation import Code
from django.utils import timezone
from notifications.email_sender import SendResult
from users.models import MembershipStatus, PublicRsvpToken

from tests._public_rsvp_helpers import make_public_rsvper

URL = "/api/community/public/my-rsvps/resend/"

PHONE = "+14155550123"
EMAIL = "sam@example.com"


def _payload(**overrides):
    base = {"phone_number": PHONE}
    base.update(overrides)
    return base


def post(api_client, **overrides):
    return api_client.post(URL, _payload(**overrides), content_type="application/json")


@pytest.mark.django_db
class TestResendManageLink:
    def test_matching_non_member_gets_link_emailed(self, api_client, fake_email_sender):
        user = make_public_rsvper(PHONE, EMAIL)

        response = post(api_client)

        assert response.status_code == 200
        # Token is never leaked into the response — email only.
        assert "token" not in response.json()

        fake_email_sender.send.assert_called_once()
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == EMAIL
        token = PublicRsvpToken.objects.get(user=user)
        assert token.token in sent["text"]
        assert "/my-rsvps?token=" in sent["text"]

    def test_extends_existing_token_keeping_same_string(self, api_client, fake_email_sender):
        user = make_public_rsvper(PHONE, EMAIL)
        original = PublicRsvpToken.issue_or_extend(user)

        post(api_client)

        assert PublicRsvpToken.objects.filter(user=user).count() == 1
        sent = fake_email_sender.send.call_args.kwargs
        assert original.token in sent["text"]

    def test_unknown_contact_is_neutral_no_email(self, api_client, fake_email_sender):
        response = post(api_client)

        assert response.status_code == 200
        fake_email_sender.send.assert_not_called()

    def test_neutral_response_is_identical_for_match_and_no_match(
        self, api_client, fake_email_sender
    ):
        no_match = post(api_client).json()
        make_public_rsvper(PHONE, EMAIL)
        match = post(api_client).json()
        assert no_match == match

    def test_member_contact_gets_no_non_member_link(self, api_client, fake_email_sender):
        member = make_public_rsvper(PHONE, EMAIL)
        member.save(
            update_fields=member.set_membership_status(MembershipStatus.ACTIVE_MEMBER, by=None)
        )

        response = post(api_client)

        assert response.status_code == 200
        fake_email_sender.send.assert_not_called()
        assert not PublicRsvpToken.objects.filter(user=member).exists()

    def test_matching_non_member_without_email_gets_nothing(self, api_client, fake_email_sender):
        # No email on file → nothing to send to, still neutral.
        user = make_public_rsvper(PHONE, "")
        user.email = None
        user.save(update_fields=["email"])

        response = post(api_client)

        assert response.status_code == 200
        fake_email_sender.send.assert_not_called()

    def test_send_failure_still_returns_neutral(self, api_client, fake_email_sender):
        make_public_rsvper(PHONE, EMAIL)
        fake_email_sender.send.return_value = SendResult(success=False, error="boom")

        response = post(api_client)

        assert response.status_code == 200
        assert response.json()["detail"] == NEUTRAL_RESPONSE

    def test_archived_non_member_gets_no_link(self, api_client, fake_email_sender):
        user = make_public_rsvper(PHONE, EMAIL)
        user.archived_at = timezone.now()
        user.save(
            update_fields=[
                "archived_at",
                *user.set_membership_status(MembershipStatus.ARCHIVED, by=None),
            ]
        )

        post(api_client)

        fake_email_sender.send.assert_not_called()

    def test_archived_member_contact_gets_no_link(self, api_client, fake_email_sender):
        member = make_public_rsvper(PHONE, EMAIL)
        member.set_membership_status(MembershipStatus.ACTIVE_MEMBER, by=None)
        member.archived_at = timezone.now()
        member.save(
            update_fields=[
                "archived_at",
                *member.set_membership_status(MembershipStatus.ARCHIVED, by=None),
            ]
        )

        post(api_client)

        fake_email_sender.send.assert_not_called()


@pytest.mark.django_db
class TestResendHoneypot:
    def test_honeypot_returns_neutral_no_side_effects(self, api_client, fake_email_sender):
        make_public_rsvper(PHONE, EMAIL)

        response = post(api_client, website="http://spam.example")

        assert response.status_code == 200
        fake_email_sender.send.assert_not_called()
        assert not PublicRsvpToken.objects.exists()


@pytest.mark.django_db
class TestResendInvalidPhone:
    def test_invalid_phone_is_neutral(self, api_client, fake_email_sender):
        response = post(api_client, phone_number="not-a-phone")

        assert response.status_code == 200
        fake_email_sender.send.assert_not_called()


@pytest.mark.django_db
class TestResendRateLimit:
    def test_fourth_request_is_limited(self, api_client, fake_email_sender):
        for _ in range(3):
            assert post(api_client).status_code == 200
        fourth = post(api_client)
        assert fourth.status_code == 429
        assert fourth.json()["detail"][0]["code"] == Code.Rate.LIMITED
