"""The two promotion paths differ in what credential the promoted user needs."""

import pytest
from community.models import AttendanceStatus, JoinRequest, JoinRequestStatus
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import NonMemberRsvpToken, User

from tests.conftest import future_iso
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
        """Re-flagging onboarding would lock them out of every endpoint."""
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


@pytest.mark.django_db
class TestTentativeWhoNeverOnboarded:
    """Status picks the tentative path, not whether they actually onboarded."""

    def test_promotion_leaves_them_able_to_recover(
        self, api_client, sample_join_request, vettor_user, open_official_event, fake_email_sender
    ):
        user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
        assert user.has_usable_password() is False
        assert user.needs_onboarding is True

        api_client.post(
            f"/api/community/events/{open_official_event.id}/rsvps/{user.pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(open_official_event.created_by),
        )

        user.refresh_from_db()
        assert user.is_member is True
        # Still flagged for onboarding — they never did it — and no fresh token
        # was minted, so /login + request-a-link is their way back in.
        assert user.needs_onboarding is True
        assert user.has_usable_password() is False

    def test_they_can_self_serve_a_login_link_after_promotion(
        self, api_client, sample_join_request, vettor_user, open_official_event, fake_email_sender
    ):
        sample_join_request.email = "never-onboarded@example.com"
        sample_join_request.save(update_fields=["email"])
        user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
        api_client.post(
            f"/api/community/events/{open_official_event.id}/rsvps/{user.pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(open_official_event.created_by),
        )
        resp = api_client.post(
            "/api/community/request-login-link/",
            {"phone_number": user.phone_number},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["delivery"] == "email"


@pytest.mark.django_db
class TestTentativeMemberRsvpsViaPublicForm:
    """A tentative applicant can use the public rsvp form instead of logging in."""

    def test_public_rsvp_resolves_to_the_existing_tentative_user(
        self, api_client, vettor_user, sample_join_request, open_official_event, fake_email_sender
    ):
        from tests._public_rsvp_helpers import make_official_event, payload, url

        tentative_user = _tentative_user_with_rsvp(
            sample_join_request, open_official_event, vettor_user
        )
        second_event = make_official_event(title="Second Potluck")
        before_count = User.objects.count()

        resp = api_client.post(
            url(second_event),
            payload(
                first_name="Whatever",
                last_name="TheyTypeHere",
                email="typed-fresh@example.com",
                phone_number=tentative_user.phone_number,
            ),
            content_type="application/json",
        )

        assert resp.status_code == 200, resp.json()
        assert User.objects.count() == before_count  # no forked account
        assert resp.json()["event"]["id"] == str(second_event.id)
        tentative_user.refresh_from_db()
        assert tentative_user.event_rsvps.filter(event=second_event).exists()

    def test_checkin_on_the_publicly_rsvpd_event_still_takes_the_tentative_path(
        self, api_client, vettor_user, sample_join_request, open_official_event, fake_email_sender
    ):
        from tests._public_rsvp_helpers import make_official_event, payload, url

        tentative_user = _tentative_user_with_rsvp(
            sample_join_request, open_official_event, vettor_user
        )
        second_event = make_official_event(
            title="Second Potluck",
            created_by=open_official_event.created_by,
            start_datetime=future_iso(days=0, minutes=30),
        )
        api_client.post(
            url(second_event),
            payload(email="typed-fresh@example.com", phone_number=tentative_user.phone_number),
            content_type="application/json",
        )
        before = tentative_user.magic_tokens.count()

        api_client.post(
            f"/api/community/events/{second_event.id}/rsvps/{tentative_user.pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(second_event.created_by),
        )

        tentative_user.refresh_from_db()
        assert tentative_user.is_member is True
        # Tentative path: mints nothing, even though this RSVP came in through
        # the public (non-member) form rather than an authenticated session.
        assert tentative_user.magic_tokens.count() == before
