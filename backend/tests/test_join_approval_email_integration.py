import pytest
from community.models import AttendanceStatus, JoinRequestStatus
from django.conf import settings
from ninja_jwt.tokens import RefreshToken

from tests.test_join_request_tentative import _tentative_user_with_rsvp, open_official_event

__all__ = ["open_official_event"]


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


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

    def test_manual_full_approve_links_to_the_login_page_not_a_magic_link(
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
        matching = [c for c in sends if c["to"] == "applicant@example.com"]
        assert len(matching) == 1
        assert f"{settings.FRONTEND_BASE_URL}/login" in matching[0]["text"]
        assert f"{settings.FRONTEND_BASE_URL}/login" in matching[0]["html"]
        assert "/magic-login/" not in matching[0]["text"]
        assert "/magic-login/" not in matching[0]["html"]

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

    def test_checkin_promotion_links_to_the_login_page(
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
        sends = [c.kwargs for c in fake_email_sender.send.call_args_list]
        matching = [c for c in sends if c["to"] == "checkin@example.com"]
        assert len(matching) == 1
        assert f"{settings.FRONTEND_BASE_URL}/login" in matching[0]["text"]
        assert "/magic-login/" not in matching[0]["text"]

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
class TestJoinApprovalEmailWhatsAppLink:
    def _approve_from_tentative(self, api_client, vettor_headers, join_request, email):
        join_request.email = email
        join_request.save(update_fields=["email"])
        api_client.patch(
            f"/api/community/join-requests/{join_request.id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **vettor_headers,
        )
        api_client.patch(
            f"/api/community/join-requests/{join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )

    def test_whatsapp_link_placeholder_is_substituted(
        self, api_client, vettor_headers, sample_join_request, fake_email_sender
    ):
        from community.models import MemberPromotionEmailTemplate, WhatsAppLinkConfig

        link_config = WhatsAppLinkConfig.get()
        link_config.link = "https://chat.whatsapp.com/abc123"
        link_config.save()
        template = MemberPromotionEmailTemplate.get()
        template.body = "join the group: ${WHATSAPP_LINK}"
        template.save()

        self._approve_from_tentative(
            api_client, vettor_headers, sample_join_request, "wa@example.com"
        )

        sends = [c.kwargs for c in fake_email_sender.send.call_args_list]
        matching = [c for c in sends if c["to"] == "wa@example.com"]
        assert len(matching) == 1
        assert "https://chat.whatsapp.com/abc123" in matching[0]["text"]
        assert "${WHATSAPP_LINK}" not in matching[0]["text"]

    def test_whatsapp_link_renders_as_an_anchor_in_html(
        self, api_client, vettor_headers, sample_join_request, fake_email_sender
    ):
        from community.models import MemberPromotionEmailTemplate, WhatsAppLinkConfig

        link_config = WhatsAppLinkConfig.get()
        link_config.link = "https://chat.whatsapp.com/abc123"
        link_config.save()
        template = MemberPromotionEmailTemplate.get()
        template.body = "join the group: ${WHATSAPP_LINK}"
        template.save()

        self._approve_from_tentative(
            api_client, vettor_headers, sample_join_request, "wa-html@example.com"
        )

        sends = [c.kwargs for c in fake_email_sender.send.call_args_list]
        matching = [c for c in sends if c["to"] == "wa-html@example.com"]
        assert len(matching) == 1
        assert 'href="https://chat.whatsapp.com/abc123"' in matching[0]["html"]

    def test_unset_whatsapp_link_substitutes_empty(
        self, api_client, vettor_headers, sample_join_request, fake_email_sender
    ):
        from community.models import MemberPromotionEmailTemplate

        template = MemberPromotionEmailTemplate.get()
        template.body = "join the group: ${WHATSAPP_LINK}"
        template.save()

        self._approve_from_tentative(
            api_client, vettor_headers, sample_join_request, "no-link@example.com"
        )

        sends = [c.kwargs for c in fake_email_sender.send.call_args_list]
        matching = [c for c in sends if c["to"] == "no-link@example.com"]
        assert len(matching) == 1
        assert "${WHATSAPP_LINK}" not in matching[0]["text"]
