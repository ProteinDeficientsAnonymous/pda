from datetime import timedelta

import pytest
from django.utils import timezone


def _non_member(phone, email=""):
    from users.models import User

    return User.objects.create_user(
        phone_number=phone,
        display_name="Rsvper",
        email=email or None,
        is_member=False,
    )


def _official_event():
    from community.models import Event, EventType

    return Event.objects.create(
        title="Potluck",
        event_type=EventType.OFFICIAL,
        start_datetime=timezone.now() + timedelta(days=7),
    )


def _community_event():
    from community.models import Event, EventType

    return Event.objects.create(
        title="Hangout",
        event_type=EventType.COMMUNITY,
        start_datetime=timezone.now() + timedelta(days=7),
    )


def _event(event_type, *, past=False):
    from community.models import Event

    offset = timedelta(days=-7 if past else 7)
    return Event.objects.create(
        title="Event",
        event_type=event_type,
        start_datetime=timezone.now() + offset,
    )


def _submit(api_client, why_join_id, phone, email):
    return api_client.post(
        "/api/community/join-request/",
        {
            "display_name": "New Applicant",
            "phone_number": phone,
            "email": email,
            "answers": {why_join_id: "Liberation."},
            "sms_consent": True,
            "guidelines_consent": True,
        },
        content_type="application/json",
    )


@pytest.mark.django_db
class TestSubmissionMemberMatch:
    def test_member_phone_match_returns_already_member(self, api_client, why_join_id):
        from users.models import User

        User.objects.create_user(phone_number="+12025551401", display_name="Member", is_member=True)
        resp = _submit(api_client, why_join_id, "+12025551401", "fresh@example.com")
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "join_request.already_member"

    def test_member_email_match_returns_already_member(self, api_client, why_join_id):
        from users.models import User

        User.objects.create_user(
            phone_number="+12025551402",
            display_name="Member",
            email="member@example.com",
            is_member=True,
        )
        resp = _submit(api_client, why_join_id, "+12025551403", "member@example.com")
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "join_request.already_member"


@pytest.mark.django_db
class TestSubmissionNonMemberAttach:
    def test_phone_match_attaches_to_existing_user(self, api_client, why_join_id):
        from community.models import JoinRequest

        existing = _non_member("+12025551410", email="rsvper@example.com")
        resp = _submit(api_client, why_join_id, "+12025551410", "rsvper@example.com")
        assert resp.status_code == 201
        jr = JoinRequest.objects.get(phone_number="+12025551410")
        assert jr.user_id == existing.id

    def test_email_match_attaches_to_existing_user(self, api_client, why_join_id):
        from community.models import JoinRequest

        existing = _non_member("+12025551411", email="byemail@example.com")
        resp = _submit(api_client, why_join_id, "+12025551412", "byemail@example.com")
        assert resp.status_code == 201
        jr = JoinRequest.objects.get(phone_number="+12025551412")
        assert jr.user_id == existing.id

    def test_attach_backfills_missing_email(self, api_client, why_join_id):
        existing = _non_member("+12025551413")  # no email saved
        _submit(api_client, why_join_id, "+12025551413", "now-known@example.com")
        existing.refresh_from_db()
        assert existing.email == "now-known@example.com"

    def test_attach_does_not_overwrite_existing_email(self, api_client, why_join_id):
        existing = _non_member("+12025551414", email="original@example.com")
        _submit(api_client, why_join_id, "+12025551414", "different@example.com")
        existing.refresh_from_db()
        assert existing.email == "original@example.com"

    def test_no_match_creates_unlinked_request(self, api_client, why_join_id):
        from community.models import JoinRequest

        resp = _submit(api_client, why_join_id, "+12025551415", "brandnew@example.com")
        assert resp.status_code == 201
        jr = JoinRequest.objects.get(phone_number="+12025551415")
        assert jr.user_id is None

    def test_phone_match_with_email_claimed_by_other_skips_backfill(self, api_client, why_join_id):
        # Phone matches an emailless non-member; the submitted email already
        # belongs to a different non-member. We attach by phone but must NOT
        # backfill the email (would break the unique-email constraint → 500).
        phone_match = _non_member("+12025551416")  # no email
        _non_member("+12025551417", email="claimed@example.com")
        resp = _submit(api_client, why_join_id, "+12025551416", "claimed@example.com")
        assert resp.status_code == 201
        phone_match.refresh_from_db()
        assert phone_match.email is None  # left untouched

    def test_phone_match_with_email_held_by_archived_skips_backfill(self, api_client, why_join_id):
        # The unique-email constraint ignores archived_at, so an archived row's
        # email still collides. Backfilling it would 500 — must be skipped.
        phone_match = _non_member("+12025551418")  # no email
        archived = _non_member("+12025551419", email="archived@example.com")
        archived.archived_at = timezone.now()
        archived.save(update_fields=["archived_at"])
        resp = _submit(api_client, why_join_id, "+12025551418", "archived@example.com")
        assert resp.status_code == 201
        phone_match.refresh_from_db()
        assert phone_match.email is None  # left untouched


@pytest.mark.django_db
class TestApprovalPromotesNonMember:
    def _approve(self, api_client, vettor_headers, jr_id):
        from community.models import JoinRequestStatus

        return api_client.patch(
            f"/api/community/join-requests/{jr_id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )

    def test_promotes_in_place_without_new_user(self, api_client, vettor_headers):
        from community.models import JoinRequest, JoinRequestStatus
        from users.models import User

        existing = _non_member("+12025551420", email="promote@example.com")
        jr = JoinRequest.objects.create(
            display_name="Promote Me",
            phone_number="+12025551420",
            email="promote@example.com",
            user=existing,
            status=JoinRequestStatus.PENDING,
        )
        before = User.objects.count()
        resp = self._approve(api_client, vettor_headers, jr.id)
        assert resp.status_code == 200
        assert User.objects.count() == before  # no new row
        existing.refresh_from_db()
        assert existing.is_member is True
        assert existing.needs_onboarding is True
        assert existing.roles.filter(name="member").exists()
        assert resp.json()["magic_link_token"] is not None
        assert resp.json()["user_id"] == str(existing.id)

    def test_revokes_outstanding_rsvp_tokens(self, api_client, vettor_headers):
        from community.models import JoinRequest, JoinRequestStatus
        from users.models import NonMemberRsvpToken

        existing = _non_member("+12025551421", email="tokens@example.com")
        token = NonMemberRsvpToken.issue(existing)
        jr = JoinRequest.objects.create(
            display_name="Token Holder",
            phone_number="+12025551421",
            email="tokens@example.com",
            user=existing,
            status=JoinRequestStatus.PENDING,
        )
        self._approve(api_client, vettor_headers, jr.id)
        token.refresh_from_db()
        assert token.revoked_at is not None

    def test_prior_rsvps_carry_to_promoted_member(self, api_client, vettor_headers):
        from community.models import EventRSVP, JoinRequest, JoinRequestStatus, RSVPStatus

        existing = _non_member("+12025551422", email="rsvps@example.com")
        event = _official_event()
        rsvp = EventRSVP.objects.create(event=event, user=existing, status=RSVPStatus.ATTENDING)
        jr = JoinRequest.objects.create(
            display_name="Has RSVPs",
            phone_number="+12025551422",
            email="rsvps@example.com",
            user=existing,
            status=JoinRequestStatus.PENDING,
        )
        self._approve(api_client, vettor_headers, jr.id)
        rsvp.refresh_from_db()
        assert rsvp.user_id == existing.id  # still attributed, now a member

    def test_deleted_user_falls_back_to_create_new(self, api_client, vettor_headers):
        from community.models import JoinRequest, JoinRequestStatus
        from users.models import User

        existing = _non_member("+12025551423", email="ghost@example.com")
        jr = JoinRequest.objects.create(
            display_name="Ghost",
            phone_number="+12025551423",
            email="ghost@example.com",
            user=existing,
            status=JoinRequestStatus.PENDING,
        )
        existing.delete()  # SET_NULL clears jr.user
        resp = self._approve(api_client, vettor_headers, jr.id)
        assert resp.status_code == 200
        assert resp.json()["magic_link_token"] is not None
        created = User.objects.get(phone_number="+12025551423")
        assert created.is_member is True
        assert created.needs_onboarding is True


@pytest.mark.django_db
class TestRsvpBreakdown:
    def _row(self, api_client, vettor_headers, jr_id):
        resp = api_client.get("/api/community/join-requests/", **vettor_headers)
        return {r["id"]: r for r in resp.json()}[str(jr_id)]

    def _rsvp(self, event, user, *, attendance=None):
        from community.models import AttendanceStatus, EventRSVP, RSVPStatus

        return EventRSVP.objects.create(
            event=event,
            user=user,
            status=RSVPStatus.ATTENDING,
            attendance=attendance or AttendanceStatus.UNKNOWN,
        )

    def test_buckets_split_by_attendance_and_type(self, api_client, vettor_headers):
        from community.models import AttendanceStatus, EventType, JoinRequest, JoinRequestStatus

        existing = _non_member("+12025551430", email="counter@example.com")
        # attended = host-marked ATTENDED, regardless of time.
        self._rsvp(
            _event(EventType.OFFICIAL, past=True),
            existing,
            attendance=AttendanceStatus.ATTENDED,
        )
        self._rsvp(
            _event(EventType.CLUB, past=True), existing, attendance=AttendanceStatus.ATTENDED
        )
        # upcoming = ATTENDING on a future event, not yet marked.
        self._rsvp(_event(EventType.OFFICIAL), existing)
        self._rsvp(_event(EventType.CLUB), existing)
        self._rsvp(_event(EventType.CLUB), existing)
        jr = JoinRequest.objects.create(
            display_name="Counter",
            phone_number="+12025551430",
            email="counter@example.com",
            user=existing,
            status=JoinRequestStatus.PENDING,
        )
        row = self._row(api_client, vettor_headers, jr.id)
        assert row["attended_official_count"] == 1
        assert row["attended_club_count"] == 1
        assert row["upcoming_official_count"] == 1
        assert row["upcoming_club_count"] == 2

    def test_community_and_non_attending_excluded(self, api_client, vettor_headers):
        from community.models import (
            EventRSVP,
            EventType,
            JoinRequest,
            JoinRequestStatus,
            RSVPStatus,
        )

        existing = _non_member("+12025551433", email="excl@example.com")
        # community type isn't a bucket; MAYBE isn't ATTENDING; a past unmarked
        # official rsvp is neither attended nor upcoming.
        self._rsvp(_community_event(), existing)
        EventRSVP.objects.create(
            event=_event(EventType.OFFICIAL), user=existing, status=RSVPStatus.MAYBE
        )
        self._rsvp(_event(EventType.OFFICIAL, past=True), existing)
        jr = JoinRequest.objects.create(
            display_name="Excluded",
            phone_number="+12025551433",
            email="excl@example.com",
            user=existing,
            status=JoinRequestStatus.PENDING,
        )
        row = self._row(api_client, vettor_headers, jr.id)
        assert row["attended_official_count"] == 0
        assert row["attended_club_count"] == 0
        assert row["upcoming_official_count"] == 0
        assert row["upcoming_club_count"] == 0

    def test_zero_when_no_attached_user(self, api_client, vettor_headers):
        from community.models import JoinRequest, JoinRequestStatus

        jr = JoinRequest.objects.create(
            display_name="Unlinked",
            phone_number="+12025551431",
            status=JoinRequestStatus.PENDING,
        )
        row = self._row(api_client, vettor_headers, jr.id)
        assert row["upcoming_official_count"] == 0
        assert row["attended_official_count"] == 0

    def test_email_matched_link_reports_user_id_and_counts(self, api_client, vettor_headers):
        # Linked by email, so the user's phone differs from the request's. user_id
        # and the rsvp counts must both resolve to the linked user (consistency).
        from community.models import EventType, JoinRequest, JoinRequestStatus

        existing = _non_member("+12025551432", email="emailmatch@example.com")
        self._rsvp(_event(EventType.OFFICIAL), existing)
        jr = JoinRequest.objects.create(
            display_name="Email Match",
            phone_number="+12025559999",  # differs from existing.phone_number
            email="emailmatch@example.com",
            user=existing,
            status=JoinRequestStatus.PENDING,
        )
        row = self._row(api_client, vettor_headers, jr.id)
        assert row["user_id"] == str(existing.id)
        assert row["upcoming_official_count"] == 1
