"""Archived-member/non-member scenarios for the public RSVP flow."""

import pytest
from community._validation import Code
from community.models import EventRSVP
from django.utils import timezone
from users.models import User

from tests._public_rsvp_helpers import make_non_member, make_official_event, post


@pytest.fixture
def official_event(db):
    return make_official_event(
        location="123 Vegan Way", whatsapp_link="https://chat.whatsapp.com/abc123"
    )


@pytest.mark.django_db
class TestArchivedMemberGate:
    def test_phone_belongs_to_archived_member(self, api_client, official_event, fake_email_sender):
        member = User.objects.create_user(
            phone_number="+14155550123", first_name="A", last_name="Member", is_member=True
        )
        member.archived_at = timezone.now()
        member.save(update_fields=["archived_at"])

        response = post(api_client, official_event)

        assert response.status_code == 409
        assert response.json()["detail"][0]["code"] == Code.Event.MEMBER_CONTACT_MUST_SIGN_IN
        assert not EventRSVP.objects.exists()
        fake_email_sender.send.assert_not_called()

    def test_email_belongs_to_archived_member(self, api_client, official_event, fake_email_sender):
        # Issue 1029 follow-up: the submitted phone isn't this member's, so this
        # is a plain email collision, not proof the submitter is that member.
        member = User.objects.create_user(
            phone_number="+14155550555",
            first_name="A",
            last_name="Member",
            email="sam@example.com",
            is_member=True,
        )
        member.archived_at = timezone.now()
        member.save(update_fields=["archived_at"])

        response = post(api_client, official_event)

        assert response.status_code == 409
        assert response.json()["detail"][0]["code"] == Code.Email.ALREADY_EXISTS
        assert not EventRSVP.objects.exists()

    def test_archived_non_member_email_holder_is_not_adopted_by_fresh_phone(
        self, api_client, official_event, fake_email_sender
    ):
        # Issue 1029: an email match alone is never proof of ownership, so a
        # fresh phone can't silently take over the archived row via its email.
        archived = make_non_member("+14155550777", "sam@example.com", name="Archived")
        archived.archived_at = timezone.now()
        archived.save(update_fields=["archived_at"])

        response = post(api_client, official_event)

        assert response.status_code == 409
        assert response.json()["detail"][0]["code"] == Code.Email.ALREADY_EXISTS
        assert not User.objects.filter(phone_number="+14155550123").exists()
        assert not EventRSVP.objects.filter(event=official_event, user=archived).exists()


@pytest.mark.django_db
class TestBackfillEmailCollision:
    def test_concurrent_email_claim_is_handled_gracefully(self):
        from community._public_rsvp_submit import _backfill_email
        from community._validation import ValidationException

        phone_match = make_non_member("+14155550123", None)
        User.objects.create_user(
            phone_number="+14155550999", first_name="Other", email="sam@example.com"
        )

        with pytest.raises(ValidationException) as exc_info:
            _backfill_email(phone_match, "sam@example.com")
        assert exc_info.value.code == Code.Email.ALREADY_EXISTS
        phone_match.refresh_from_db()
        assert phone_match.email is None
