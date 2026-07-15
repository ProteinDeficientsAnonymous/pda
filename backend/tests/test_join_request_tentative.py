from datetime import timedelta

import pytest
from community._validation import Code
from community.models import (
    AttendanceStatus,
    Event,
    EventRSVP,
    EventType,
    JoinRequestStatus,
    RSVPStatus,
)
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import NonMemberRsvpToken, User

from tests._asserts import assert_error_code


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.mark.django_db
class TestTentativeApprove:
    def test_pending_to_tentative_succeeds(self, api_client, vettor_headers, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == JoinRequestStatus.TENTATIVE
        sample_join_request.refresh_from_db()
        assert sample_join_request.status == JoinRequestStatus.TENTATIVE

    def test_tentative_creates_linked_non_member(
        self, api_client, vettor_headers, sample_join_request
    ):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        sample_join_request.refresh_from_db()
        user = sample_join_request.user
        assert user is not None
        assert user.is_member is False
        assert not user.roles.filter(name="member").exists()

    def test_tentative_issues_rsvp_token(self, api_client, vettor_headers, sample_join_request):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **vettor_headers,
        )
        sample_join_request.refresh_from_db()
        assert NonMemberRsvpToken.objects.filter(
            user=sample_join_request.user, revoked_at__isnull=True
        ).exists()

    def test_tentative_sends_no_email(
        self, api_client, vettor_headers, sample_join_request, fake_email_sender
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **vettor_headers,
        )
        fake_email_sender.send.assert_not_called()

    def test_tentative_no_magic_token_in_response(
        self, api_client, vettor_headers, sample_join_request
    ):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.json()["magic_link_token"] is None

    def test_tentative_requires_permission(self, api_client, auth_headers, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_tentative_not_a_member_on_directory(
        self, api_client, vettor_headers, sample_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **vettor_headers,
        )
        sample_join_request.refresh_from_db()
        member_ids = set(User.objects.members().values_list("id", flat=True))
        assert sample_join_request.user.id not in member_ids


@pytest.fixture
def open_official_event(db):
    host = User.objects.create_user(phone_number="+12025557000", first_name="Host")
    return Event.objects.create(
        title="Official Meetup",
        start_datetime=timezone.now() + timedelta(minutes=30),
        end_datetime=timezone.now() + timedelta(hours=2),
        rsvp_enabled=True,
        event_type=EventType.OFFICIAL,
        created_by=host,
    )


def _tentative_user_with_rsvp(join_request, event, vettor):
    from community._join_request_approval import _provision_tentative_user

    _provision_tentative_user(join_request, vettor)
    join_request.status = JoinRequestStatus.TENTATIVE
    join_request.save(update_fields=["status"])
    join_request.refresh_from_db()
    EventRSVP.objects.create(event=event, user=join_request.user, status=RSVPStatus.ATTENDING)
    return join_request.user


@pytest.mark.django_db
class TestCheckInPromotion:
    def _mark(self, api_client, event, user, headers, attendance):
        return api_client.post(
            f"/api/community/events/{event.id}/rsvps/{user.pk}/attendance/",
            {"attendance": attendance},
            content_type="application/json",
            **headers,
        )

    def test_attended_official_promotes(
        self, api_client, vettor_user, sample_join_request, open_official_event, fake_email_sender
    ):
        sample_join_request.email = "promote@example.com"
        sample_join_request.save(update_fields=["email"])
        user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
        host_headers = _auth(open_official_event.created_by)
        resp = self._mark(
            api_client, open_official_event, user, host_headers, AttendanceStatus.ATTENDED
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        sample_join_request.refresh_from_db()
        assert user.is_member is True
        assert user.roles.filter(name="member").exists()
        assert sample_join_request.status == JoinRequestStatus.APPROVED
        fake_email_sender.send.assert_called()

    def test_attended_club_promotes(
        self, api_client, vettor_user, sample_join_request, open_official_event, fake_email_sender
    ):
        open_official_event.event_type = EventType.CLUB
        open_official_event.save(update_fields=["event_type"])
        user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
        host_headers = _auth(open_official_event.created_by)
        resp = self._mark(
            api_client, open_official_event, user, host_headers, AttendanceStatus.ATTENDED
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.is_member is True

    def test_attended_community_does_not_promote(
        self, api_client, vettor_user, sample_join_request, open_official_event, fake_email_sender
    ):
        open_official_event.event_type = EventType.COMMUNITY
        open_official_event.save(update_fields=["event_type"])
        user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
        host_headers = _auth(open_official_event.created_by)
        resp = self._mark(
            api_client, open_official_event, user, host_headers, AttendanceStatus.ATTENDED
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        sample_join_request.refresh_from_db()
        assert user.is_member is False
        assert sample_join_request.status == JoinRequestStatus.TENTATIVE
        fake_email_sender.send.assert_not_called()

    def test_attended_non_tentative_user_no_op(
        self, api_client, open_official_event, fake_email_sender
    ):
        non_member = User.objects.create(
            phone_number="+12025557111", first_name="Plain", is_member=False
        )
        EventRSVP.objects.create(
            event=open_official_event, user=non_member, status=RSVPStatus.ATTENDING
        )
        host_headers = _auth(open_official_event.created_by)
        resp = self._mark(
            api_client, open_official_event, non_member, host_headers, AttendanceStatus.ATTENDED
        )
        assert resp.status_code == 200
        non_member.refresh_from_db()
        assert non_member.is_member is False
        fake_email_sender.send.assert_not_called()

    def test_no_show_does_not_promote(
        self, api_client, vettor_user, sample_join_request, open_official_event, fake_email_sender
    ):
        user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
        host_headers = _auth(open_official_event.created_by)
        resp = self._mark(
            api_client, open_official_event, user, host_headers, AttendanceStatus.NO_SHOW
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        sample_join_request.refresh_from_db()
        assert user.is_member is False
        assert sample_join_request.status == JoinRequestStatus.TENTATIVE


@pytest.mark.django_db
class TestManualFullApproveFromTentative:
    def _to_tentative(self, api_client, jr, headers):
        api_client.patch(
            f"/api/community/join-requests/{jr.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **headers,
        )
        jr.refresh_from_db()

    def test_tentative_to_approved_promotes_and_emails(
        self, api_client, vettor_headers, sample_join_request, fake_email_sender
    ):
        sample_join_request.email = "sprout@example.com"
        sample_join_request.save(update_fields=["email"])
        self._to_tentative(api_client, sample_join_request, vettor_headers)
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        sample_join_request.refresh_from_db()
        assert sample_join_request.status == JoinRequestStatus.APPROVED
        assert sample_join_request.user.is_member is True
        fake_email_sender.send.assert_called()

    def test_tentative_to_rejected_does_not_promote(
        self, api_client, vettor_headers, sample_join_request, fake_email_sender
    ):
        self._to_tentative(api_client, sample_join_request, vettor_headers)
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.REJECTED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        sample_join_request.refresh_from_db()
        assert sample_join_request.status == JoinRequestStatus.REJECTED
        assert sample_join_request.user.is_member is False

    def test_approved_cannot_be_redecided(self, api_client, vettor_headers, sample_join_request):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.REJECTED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.JoinRequest.ALREADY_DECIDED)


@pytest.mark.django_db
class TestJoinApprovalEmail:
    def test_manual_full_approve_from_tentative_sends_to_applicant(
        self, api_client, vettor_headers, sample_join_request, fake_email_sender
    ):
        sample_join_request.email = "applicant@example.com"
        sample_join_request.save(update_fields=["email"])
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **vettor_headers,
        )
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        sends = [c.kwargs for c in fake_email_sender.send.call_args_list]
        recipients = [c["to"] for c in sends]
        subjects = [c["subject"] for c in sends]
        assert "applicant@example.com" in recipients
        assert any("welcome to pda" in s for s in subjects)

    def test_checkin_promotion_sends_to_applicant(
        self, api_client, vettor_user, sample_join_request, open_official_event, fake_email_sender
    ):
        sample_join_request.email = "checkin@example.com"
        sample_join_request.save(update_fields=["email"])
        user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
        host_headers = _auth(open_official_event.created_by)
        api_client.post(
            f"/api/community/events/{open_official_event.id}/rsvps/{user.pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **host_headers,
        )
        recipients = [c.kwargs["to"] for c in fake_email_sender.send.call_args_list]
        assert "checkin@example.com" in recipients

    def test_uses_editable_message_with_first_name_substitution(
        self, api_client, vettor_headers, sample_join_request, fake_email_sender
    ):
        from community.models import MemberPromotionEmailTemplate

        template = MemberPromotionEmailTemplate.get()
        template.body = "hey ${FIRST_NAME} — you came through, you're in for real now"
        template.save()
        sample_join_request.email = "custom@example.com"
        sample_join_request.save(update_fields=["email"])
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **vettor_headers,
        )
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        sends = [c.kwargs for c in fake_email_sender.send.call_args_list]
        matching = [c for c in sends if c["to"] == "custom@example.com"]
        assert len(matching) == 1
        assert "you came through, you're in for real now" in matching[0]["text"]
        assert sample_join_request.first_name in matching[0]["text"]
        assert "${FIRST_NAME}" not in matching[0]["text"]

    def test_html_email_escapes_editable_message_body(
        self, api_client, vettor_headers, sample_join_request, fake_email_sender
    ):
        from community.models import MemberPromotionEmailTemplate

        template = MemberPromotionEmailTemplate.get()
        template.body = "hi <script>alert(1)</script> & welcome"
        template.save()
        sample_join_request.email = "html-check@example.com"
        sample_join_request.save(update_fields=["email"])
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **vettor_headers,
        )
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        sends = [c.kwargs for c in fake_email_sender.send.call_args_list]
        matching = [c for c in sends if c["to"] == "html-check@example.com"]
        assert len(matching) == 1
        html = matching[0]["html"]
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
        assert "&amp; welcome" in html

    def test_tentative_message_template_does_not_affect_promotion_email(
        self, api_client, vettor_headers, sample_join_request, fake_email_sender
    ):
        from community.models import (
            MemberPromotionEmailTemplate,
            TentativeApprovalMessageTemplate,
        )

        tentative_template = TentativeApprovalMessageTemplate.get()
        tentative_template.body = "hi ${FIRST_NAME}, from ${SENDER_NAME} — you're tentatively in"
        tentative_template.save()
        promotion_template = MemberPromotionEmailTemplate.get()
        promotion_template.body = "you're fully in now, ${FIRST_NAME}"
        promotion_template.save()
        sample_join_request.email = "separate-templates@example.com"
        sample_join_request.save(update_fields=["email"])
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **vettor_headers,
        )
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        sends = [c.kwargs for c in fake_email_sender.send.call_args_list]
        matching = [c for c in sends if c["to"] == "separate-templates@example.com"]
        assert len(matching) == 1
        assert "you're fully in now" in matching[0]["text"]
        assert "tentatively in" not in matching[0]["text"]


@pytest.mark.django_db
class TestTentativeRsvpEvents:
    def test_list_includes_rsvpd_events(
        self, api_client, vettor_headers, vettor_user, sample_join_request, open_official_event
    ):
        user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        row = next(r for r in response.json() if r["user_id"] == str(user.id))
        assert [e["title"] for e in row["rsvp_events"]] == ["Official Meetup"]

    def test_list_includes_future_events(
        self, api_client, vettor_headers, vettor_user, sample_join_request, open_official_event
    ):
        user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        row = next(r for r in response.json() if r["user_id"] == str(user.id))
        assert row["rsvp_events"][0]["start_datetime"] is not None
        assert open_official_event.start_datetime > timezone.now()

    def test_list_excludes_non_attending_rsvps(
        self, api_client, vettor_headers, vettor_user, sample_join_request, open_official_event
    ):
        from community._join_request_approval import _provision_tentative_user

        _provision_tentative_user(sample_join_request, vettor_user)
        sample_join_request.status = JoinRequestStatus.TENTATIVE
        sample_join_request.save(update_fields=["status"])
        sample_join_request.refresh_from_db()
        EventRSVP.objects.create(
            event=open_official_event,
            user=sample_join_request.user,
            status=RSVPStatus.CANT_GO,
        )
        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        row = next(r for r in response.json() if r["user_id"] == str(sample_join_request.user.id))
        assert row["rsvp_events"] == []

    def test_list_empty_when_no_rsvps(self, api_client, vettor_headers, sample_join_request):
        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        row = next(r for r in response.json() if r["id"] == str(sample_join_request.id))
        assert row["rsvp_events"] == []

    def test_list_excludes_non_bucketed_event_types(
        self, api_client, vettor_headers, vettor_user, sample_join_request, open_official_event
    ):
        open_official_event.event_type = EventType.COMMUNITY
        open_official_event.save(update_fields=["event_type"])
        user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        row = next(r for r in response.json() if r["user_id"] == str(user.id))
        assert row["rsvp_events"] == []

    def test_list_orders_tbd_events_last(
        self, api_client, vettor_headers, vettor_user, sample_join_request, open_official_event
    ):
        host = open_official_event.created_by
        tbd_event = Event.objects.create(
            title="TBD Meetup",
            start_datetime=None,
            end_datetime=None,
            datetime_tbd=True,
            rsvp_enabled=True,
            event_type=EventType.OFFICIAL,
            created_by=host,
        )
        user = _tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
        EventRSVP.objects.create(event=tbd_event, user=user, status=RSVPStatus.ATTENDING)
        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        row = next(r for r in response.json() if r["user_id"] == str(user.id))
        assert [e["title"] for e in row["rsvp_events"]] == ["Official Meetup", "TBD Meetup"]
