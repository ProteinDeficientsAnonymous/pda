"""Tests for join request submission."""

import pytest
from community.models import JoinRequestStatus
from notifications.models import Notification, NotificationType
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def why_join_id(db):
    from community.models import JoinFormQuestion

    q = JoinFormQuestion.objects.filter(required=True).first()
    return str(q.id) if q else ""


@pytest.mark.django_db
class TestJoinRequestSubmission:
    def test_submit_join_request(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "+12025551234",
                "answers": {why_join_id: "I want to connect with other vegans."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "Leafy G"
        assert data["phone_number"] == "+12025551234"
        assert len(data["answers"]) >= 1

    def test_submit_join_request_missing_required_answer(self, api_client):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "+12025551234",
                "answers": {},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_join_request_invalid_display_name(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy123",
                "phone_number": "+12025551234",
                "answers": {why_join_id: "Liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_join_request_invalid_phone(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "not-a-number",
                "answers": {why_join_id: "Liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_join_request_optional_answers(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "+13105551234",
                "answers": {why_join_id: "Liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    def test_join_request_sends_email_when_vetting_email_set(
        self, api_client, settings, why_join_id
    ):
        settings.VETTING_EMAIL = "vetting@pda.org"
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        from django.core import mail

        api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Test Person",
                "phone_number": "+14155551234",
                "answers": {why_join_id: "Because liberation."},
            },
            content_type="application/json",
        )
        assert len(mail.outbox) == 1
        assert "Test Person" in mail.outbox[0].subject
        assert mail.outbox[0].to == ["vetting@pda.org"]

    def test_join_request_no_email_when_vetting_email_unset(
        self, api_client, settings, why_join_id
    ):
        settings.VETTING_EMAIL = ""
        from django.core import mail

        api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Test Person",
                "phone_number": "+14155551234",
                "answers": {why_join_id: "Because liberation."},
            },
            content_type="application/json",
        )
        assert len(mail.outbox) == 0

    def test_submit_empty_display_name(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "   ",
                "phone_number": "+12025550701",
                "answers": {why_join_id: "I care"},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_missing_required_answer(self, api_client):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Alice",
                "phone_number": "+12025550702",
                "answers": {},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_display_name_too_long(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "A" * 65,
                "phone_number": "+12025550703",
                "answers": {why_join_id: "I care"},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_display_name_with_numbers(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Alice2",
                "phone_number": "+12025550704",
                "answers": {why_join_id: "I care"},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_display_name_with_email_rejected(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "user@example.com",
                "phone_number": "+12025550705",
                "answers": {why_join_id: "I care"},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_display_name_with_url_rejected(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "http://evil.com",
                "phone_number": "+12025550706",
                "answers": {why_join_id: "I care"},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "name,phone",
        [
            ("José O'Brien", "+12025550707"),
            ("Müller-Schmidt", "+12025550709"),
            ("Юлия К", "+12025550710"),
            ("田中 太郎", "+12025550711"),
        ],
    )
    def test_submit_display_name_unicode_accepted(self, api_client, why_join_id, name, phone):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": name,
                "phone_number": phone,
                "answers": {why_join_id: "Collective liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201, f"Expected 201 for name: {name!r}"

    def test_submit_display_name_hyphen_apostrophe_accepted(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Mary-Jane O'Brien",
                "phone_number": "+12025550708",
                "answers": {why_join_id: "Collective liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    def test_default_status_is_pending(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "New Sprout",
                "phone_number": "+19175551234",
                "answers": {why_join_id: "Collective liberation matters."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        assert response.json()["status"] == JoinRequestStatus.PENDING

    def test_submit_creates_notifications_for_approvers(self, api_client, why_join_id, db):
        from users.models import User

        approver = User.objects.create_user(
            phone_number="+12025559001", password="pass", display_name="Approver"
        )
        role = Role.objects.create(name="vetter", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS])
        approver.roles.add(role)

        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy New",
                "phone_number": "+12025559002",
                "answers": {why_join_id: "Collective liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        notif = Notification.objects.get(recipient=approver)
        assert notif.notification_type == NotificationType.JOIN_REQUEST
        assert "Leafy New" in notif.message

    def test_submit_notification_failure_does_not_block(self, api_client, why_join_id, monkeypatch):
        def _fail(*args, **kwargs):
            raise RuntimeError("notification service down")

        monkeypatch.setattr("community._join_requests.create_join_request_notifications", _fail)
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "+12025559003",
                "answers": {why_join_id: "Liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201
