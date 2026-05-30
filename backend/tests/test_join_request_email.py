"""Tests for email validation on join request submission."""

import pytest


@pytest.fixture
def why_join_id(db):
    from community.models import JoinFormQuestion

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
        from community.models import JoinRequest

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
