"""Tests for the public "resend my manage link" recovery endpoint.

POST /api/community/public/my-rsvps/resend/ — no auth. Given a phone (email
optional), re-sends a non-member's scoped manage link so they can recover access
without re-submitting an RSVP. Always returns the same neutral 200 (no enumeration).
"""

import pytest
from community._public_rsvp_resend import _NEUTRAL_RESPONSE
from community._validation import Code
from django.utils import timezone
from notifications.email_sender import SendResult
from users.models import NonMemberRsvpToken

from tests._public_rsvp_helpers import make_non_member

URL = "/api/community/public/my-rsvps/resend/"

PHONE = "+14155550123"
EMAIL = "sam@example.com"


def _payload(**overrides):
    base = {"email": EMAIL, "phone_number": PHONE}
    base.update(overrides)
    return base


def post(api_client, **overrides):
    return api_client.post(URL, _payload(**overrides), content_type="application/json")


@pytest.mark.django_db
class TestResendManageLink:
    def test_matching_non_member_gets_link_emailed(self, api_client, fake_email_sender):
        user = make_non_member(PHONE, EMAIL)

        response = post(api_client)

        assert response.status_code == 200
        # Token is never leaked into the response — email only.
        assert "token" not in response.json()

        fake_email_sender.send.assert_called_once()
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == EMAIL
        token = NonMemberRsvpToken.objects.get(user=user)
        assert token.token in sent["text"]
        assert "/my-rsvps?token=" in sent["text"]

    def test_extends_existing_token_keeping_same_string(self, api_client, fake_email_sender):
        user = make_non_member(PHONE, EMAIL)
        original = NonMemberRsvpToken.issue_or_extend(user)

        post(api_client)

        assert NonMemberRsvpToken.objects.filter(user=user).count() == 1
        sent = fake_email_sender.send.call_args.kwargs
        assert original.token in sent["text"]

    def test_email_match_only_still_resends(self, api_client, fake_email_sender):
        # Phone doesn't match, but the email does — still a valid recovery.
        make_non_member("+14155559999", EMAIL)

        response = post(api_client)

        assert response.status_code == 200
        fake_email_sender.send.assert_called_once()

    def test_phone_only_no_email_field_still_resends(self, api_client, fake_email_sender):
        # Email is optional; phone alone recovers, link goes to the on-file address.
        make_non_member(PHONE, EMAIL)

        response = api_client.post(URL, {"phone_number": PHONE}, content_type="application/json")

        assert response.status_code == 200
        fake_email_sender.send.assert_called_once()
        assert fake_email_sender.send.call_args.kwargs["to"] == EMAIL

    def test_unknown_contact_is_neutral_no_email(self, api_client, fake_email_sender):
        response = post(api_client)

        assert response.status_code == 200
        fake_email_sender.send.assert_not_called()

    def test_neutral_response_is_identical_for_match_and_no_match(
        self, api_client, fake_email_sender
    ):
        no_match = post(api_client).json()
        make_non_member(PHONE, EMAIL)
        match = post(api_client).json()
        assert no_match == match

    def test_member_contact_gets_no_non_member_link(self, api_client, fake_email_sender):
        member = make_non_member(PHONE, EMAIL)
        member.is_member = True
        member.save(update_fields=["is_member"])

        response = post(api_client)

        assert response.status_code == 200
        fake_email_sender.send.assert_not_called()
        assert not NonMemberRsvpToken.objects.filter(user=member).exists()

    def test_member_email_match_gets_no_link(self, api_client, fake_email_sender):
        # Member owns the email; a different phone is supplied. Must not leak a link.
        member = make_non_member("+14155559999", EMAIL)
        member.is_member = True
        member.save(update_fields=["is_member"])

        post(api_client)

        fake_email_sender.send.assert_not_called()

    def test_matching_non_member_without_email_gets_nothing(self, api_client, fake_email_sender):
        # No email on file → nothing to send to, still neutral.
        user = make_non_member(PHONE, "")
        user.email = None
        user.save(update_fields=["email"])

        response = post(api_client)

        assert response.status_code == 200
        fake_email_sender.send.assert_not_called()

    def test_send_failure_still_returns_neutral(self, api_client, fake_email_sender):
        make_non_member(PHONE, EMAIL)
        fake_email_sender.send.return_value = SendResult(success=False, error="boom")

        response = post(api_client)

        assert response.status_code == 200
        assert response.json()["detail"] == _NEUTRAL_RESPONSE

    def test_archived_non_member_still_gets_link(self, api_client, fake_email_sender):
        user = make_non_member(PHONE, EMAIL)
        user.archived_at = timezone.now()
        user.save(update_fields=["archived_at"])

        post(api_client)

        fake_email_sender.send.assert_called_once()

    def test_archived_member_contact_gets_no_link(self, api_client, fake_email_sender):
        member = make_non_member(PHONE, EMAIL)
        member.is_member = True
        member.archived_at = timezone.now()
        member.save(update_fields=["is_member", "archived_at"])

        post(api_client)

        fake_email_sender.send.assert_not_called()


@pytest.mark.django_db
class TestResendHoneypot:
    def test_honeypot_returns_neutral_no_side_effects(self, api_client, fake_email_sender):
        make_non_member(PHONE, EMAIL)

        response = post(api_client, website="http://spam.example")

        assert response.status_code == 200
        fake_email_sender.send.assert_not_called()
        assert not NonMemberRsvpToken.objects.exists()


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
