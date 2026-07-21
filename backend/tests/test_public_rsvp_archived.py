"""Archived-member/non-member scenarios for the public RSVP flow (Issue 1002, 1003).

Archiving a user (backend/users/_management.py delete_user) only sets
archived_at — it never clears is_member. So an archived member row still has
is_member=True forever, and still occupies its phone number (globally unique)
and email (partial unique constraint, no archived_at exception). These tests
prove the member-gate in _resolve_non_member sees archived members (no 500,
no silent identity takeover) and that _backfill_email degrades gracefully on
a collision instead of raising an uncaught IntegrityError.
"""

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
        # Without the fix: phone_match's archived_at__isnull=True filter misses
        # this row, the gate never fires, and _create_non_member's
        # get_or_create matches it via the unique phone constraint, returning
        # the member row — issue_or_extend then raises for is_member and 500s.
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
        assert response.json()["detail"][0]["code"] == Code.Event.MEMBER_CONTACT_MUST_SIGN_IN
        assert not EventRSVP.objects.exists()

    def test_archived_non_member_email_holder_is_reused(
        self, api_client, official_event, fake_email_sender
    ):
        # Archived non-members aren't members-in-hiding — same reuse path as a
        # live non-member, consistent with _join_request_submit's precedent.
        archived = make_non_member("+14155550777", "sam@example.com", name="Archived")
        archived.archived_at = timezone.now()
        archived.save(update_fields=["archived_at"])

        response = post(api_client, official_event)

        assert response.status_code == 200
        assert not User.objects.filter(phone_number="+14155550123").exists()
        assert EventRSVP.objects.filter(event=official_event, user=archived).exists()


@pytest.mark.django_db
class TestBackfillEmailCollision:
    def test_concurrent_email_claim_is_handled_gracefully(self):
        # _backfill_email had no guard around its save(), so a unique-email
        # collision raised an uncaught IntegrityError (500). This simulates
        # the race window between _resolve_non_member's pre-check and the
        # save: another row claims the email in between.
        from community._public_rsvp_submit import _backfill_email
        from community._validation import ValidationException

        phone_match = make_non_member("+14155550123", None)
        User.objects.create_user(
            phone_number="+14155550999", first_name="Other", email="sam@example.com"
        )

        with pytest.raises(ValidationException) as exc_info:
            _backfill_email(phone_match, "sam@example.com")
        assert exc_info.value.code == Code.Email.ALREADY_EXISTS
        # The failed save must not have persisted — the DB row stays blank.
        phone_match.refresh_from_db()
        assert phone_match.email is None


# The resend endpoint (POST /public/my-rsvps/resend/) shares the same
# archived-member lookup shape — its tests live in test_public_rsvp_resend.py
# (TestResendManageLink.test_archived_member_contact_gets_no_link).
