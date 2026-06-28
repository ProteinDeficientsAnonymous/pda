"""Tests for email validation on join request submission."""

import pytest
from community._join_requests import _send_join_request_email
from community._shared import flatten_to_single_line
from community.models import JoinFormQuestion, JoinRequest
from django.core import mail


@pytest.fixture
def why_join_id(db):
    q = JoinFormQuestion.objects.filter(required=True).first()
    return str(q.id) if q else ""


@pytest.mark.django_db
class TestJoinRequestEmail:
    def test_missing_email_rejected(self, api_client):
        resp = api_client.post(
            "/api/community/join-request/",
            data={
                "display_name": "Test",
                "phone_number": "+12025550101",
                "answers": {},
                "sms_consent": True,
                "guidelines_consent": True,
            },
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_malformed_email_rejected(self, api_client):
        resp = api_client.post(
            "/api/community/join-request/",
            data={
                "display_name": "Test",
                "phone_number": "+12025550101",
                "answers": {},
                "sms_consent": True,
                "guidelines_consent": True,
                "email": "not-an-email",
            },
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_valid_email_persisted_lowercased(self, api_client, why_join_id):
        resp = api_client.post(
            "/api/community/join-request/",
            data={
                "display_name": "Test Person",
                "phone_number": "+12025550101",
                "answers": {why_join_id: "Collective liberation."},
                "sms_consent": True,
                "guidelines_consent": True,
                "email": "Foo@Example.com",
            },
            content_type="application/json",
        )
        assert resp.status_code == 201, resp.content
        jr = JoinRequest.objects.get(phone_number="+12025550101")
        assert jr.email == "foo@example.com"


class TestVettingEmailHeaderInjection:
    """Issue 457 — CR/LF in interpolated values must not forge email headers."""

    def test_flatten_to_single_line_collapses_crlf(self):
        out = flatten_to_single_line("Eve\r\nBcc: victim@example.com")
        assert "\n" not in out
        assert "\r" not in out
        assert out == "Eve Bcc: victim@example.com"

    @pytest.mark.django_db
    def test_vetting_email_subject_is_single_line(self, settings):
        settings.VETTING_EMAIL = "vetting@example.com"
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        mail.outbox = []

        _send_join_request_email(
            display_name="Mallory\r\nSubject: spoofed",
            phone="+12025550101",
            custom_answers={},
        )
        assert len(mail.outbox) == 1
        subject = mail.outbox[0].subject
        assert "\n" not in subject
        assert "\r" not in subject
