"""The two promotion paths differ in what credential the promoted user needs.

A publicly-RSVP'd non-member has never onboarded and has no password, so
promotion mints the magic token that replaces their revoked rsvp tokens. A
tentatively-approved applicant onboarded on first login, so promotion must
leave their password, name and onboarding state alone.
"""

import pytest
from community.models import AttendanceStatus, JoinRequest, JoinRequestStatus
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import NonMemberRsvpToken, User

from tests.test_join_request_tentative import _tentative_user_with_rsvp, open_official_event

__all__ = ["open_official_event"]


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


def _approve(api_client, vettor_headers, jr_id):
    return api_client.patch(
        f"/api/community/join-requests/{jr_id}/",
        {"status": JoinRequestStatus.APPROVED},
        content_type="application/json",
        **vettor_headers,
    )


@pytest.mark.django_db
class TestPromotePublicNonMember:
    def _public_non_member_request(self):
        user = User.objects.create_user(
            phone_number="+12025551900",
            first_name="Rsvper",
            email="public@example.com",
            is_member=False,
        )
        NonMemberRsvpToken.issue(user)
        jr = JoinRequest.objects.create(
            first_name="Public",
            last_name="Rsvper",
            phone_number="+12025551900",
            email="public@example.com",
            user=user,
            status=JoinRequestStatus.PENDING,
        )
        return user, jr

    def test_mints_the_token_that_replaces_their_revoked_rsvp_tokens(
        self, api_client, vettor_headers
    ):
        user, jr = self._public_non_member_request()
        before = user.magic_tokens.count()
        resp = _approve(api_client, vettor_headers, jr.id)
        assert resp.status_code == 200
        assert resp.json()["magic_link_token"] is not None
        assert user.magic_tokens.count() == before + 1

    def test_sends_them_through_onboarding(self, api_client, vettor_headers):
        user, jr = self._public_non_member_request()
        _approve(api_client, vettor_headers, jr.id)
        user.refresh_from_db()
        assert user.is_member is True
        assert user.needs_onboarding is True


@pytest.fixture
def onboarded_tentative(sample_join_request, vettor_user, open_official_event):
    """A tentative applicant who has already onboarded: password, own name."""
    user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
    user.first_name = "Chosen"
    user.last_name = "Name"
    user.needs_onboarding = False
    user.onboarded_at = timezone.now()
    user.set_password("theirownpass123")
    user.save()
    return user, open_official_event


@pytest.mark.django_db
class TestPromoteTentativeMember:
    def test_checkin_promotion_mints_no_token(
        self, api_client, onboarded_tentative, fake_email_sender
    ):
        user, event = onboarded_tentative
        before = user.magic_tokens.count()
        api_client.post(
            f"/api/community/events/{event.id}/rsvps/{user.pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(event.created_by),
        )
        user.refresh_from_db()
        assert user.is_member is True
        assert user.magic_tokens.count() == before

    def test_manual_promotion_returns_no_magic_token(
        self, api_client, vettor_headers, onboarded_tentative, fake_email_sender
    ):
        user, _ = onboarded_tentative
        join_request = user.join_requests.get()
        resp = _approve(api_client, vettor_headers, join_request.id)
        assert resp.status_code == 200
        assert resp.json()["magic_link_token"] is None
        user.refresh_from_db()
        assert user.is_member is True

    def test_promotion_leaves_onboarding_done(
        self, api_client, onboarded_tentative, fake_email_sender
    ):
        """Re-flagging onboarding would lock them out — the auth gate blocks
        every endpoint until it is cleared."""
        user, event = onboarded_tentative
        api_client.post(
            f"/api/community/events/{event.id}/rsvps/{user.pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(event.created_by),
        )
        user.refresh_from_db()
        assert user.needs_onboarding is False

    def test_promotion_keeps_the_name_they_chose_at_onboarding(
        self, api_client, onboarded_tentative, fake_email_sender
    ):
        user, event = onboarded_tentative
        api_client.post(
            f"/api/community/events/{event.id}/rsvps/{user.pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(event.created_by),
        )
        user.refresh_from_db()
        assert user.first_name == "Chosen"
        assert user.last_name == "Name"

    def test_promotion_keeps_their_password(
        self, api_client, onboarded_tentative, fake_email_sender
    ):
        user, event = onboarded_tentative
        api_client.post(
            f"/api/community/events/{event.id}/rsvps/{user.pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(event.created_by),
        )
        user.refresh_from_db()
        assert user.check_password("theirownpass123")

    def test_a_nameless_tentative_user_is_rejected(self, sample_join_request):
        """Issue 733 — no approval path may produce a member with no first name."""
        from community._join_request_approval import _promote_tentative_member
        from community._validation import ValidationException

        user = User.objects.create_user(
            phone_number="+12025551901", first_name="Temp", is_member=False
        )
        user.first_name = ""
        user.save(update_fields=["first_name"])
        with pytest.raises(ValidationException):
            _promote_tentative_member(user, sample_join_request)
