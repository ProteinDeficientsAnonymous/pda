"""Integration tests for email sending on the member-invite endpoint (Issue 859)."""

from unittest.mock import patch

import pytest
from community.models import Event
from ninja_jwt.tokens import RefreshToken
from notifications.email_sender import SendResult
from users.models import User

from tests.conftest import future_iso


def _make_user(phone: str, name: str = "", email: str = "") -> User:
    return User.objects.create_user(
        phone_number=phone, password="pass", first_name=name, email=email
    )


def _auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture
def inviter(db) -> User:
    return _make_user("+12025550101", "Alice")


@pytest.fixture
def invitee_with_email(db) -> User:
    return _make_user("+12025550102", "Bob", email="bob@example.com")


@pytest.fixture
def invitee_without_email(db) -> User:
    return _make_user("+12025550103", "Carol", email="")


@pytest.fixture
def sample_event(inviter) -> Event:
    return Event.objects.create(
        title="Test Event",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        created_by=inviter,
    )


@pytest.mark.django_db
class TestEventInviteEmailIntegration:
    def test_sends_email_to_invitee_with_email(
        self, api_client, inviter, invitee_with_email, sample_event
    ):
        with patch("community._event_invite_email.send_event_invite_email") as mock_send:
            mock_send.return_value = SendResult(success=True)
            response = api_client.post(
                f"/api/community/events/{sample_event.id}/invitations/",
                {"user_ids": [str(invitee_with_email.pk)]},
                content_type="application/json",
                **_auth_headers(inviter),
            )
        assert response.status_code == 200
        mock_send.assert_called_once()
        assert mock_send.call_args.kwargs["details"].to == "bob@example.com"

    def test_skips_email_for_invitee_without_email(
        self, api_client, inviter, invitee_without_email, sample_event
    ):
        with patch("community._event_invite_email.send_event_invite_email") as mock_send:
            response = api_client.post(
                f"/api/community/events/{sample_event.id}/invitations/",
                {"user_ids": [str(invitee_without_email.pk)]},
                content_type="application/json",
                **_auth_headers(inviter),
            )
        assert response.status_code == 200
        mock_send.assert_not_called()

    def test_endpoint_succeeds_even_if_email_send_raises(
        self, api_client, inviter, invitee_with_email, sample_event
    ):
        with patch(
            "community._event_invite_email.send_event_invite_email",
            side_effect=RuntimeError("smtp down"),
        ):
            response = api_client.post(
                f"/api/community/events/{sample_event.id}/invitations/",
                {"user_ids": [str(invitee_with_email.pk)]},
                content_type="application/json",
                **_auth_headers(inviter),
            )
        assert response.status_code == 200

    def test_endpoint_succeeds_when_email_send_reports_failure(
        self, api_client, inviter, invitee_with_email, sample_event
    ):
        with patch("community._event_invite_email.send_event_invite_email") as mock_send:
            mock_send.return_value = SendResult(success=False, error="bounced")
            response = api_client.post(
                f"/api/community/events/{sample_event.id}/invitations/",
                {"user_ids": [str(invitee_with_email.pk)]},
                content_type="application/json",
                **_auth_headers(inviter),
            )
        assert response.status_code == 200
        mock_send.assert_called_once()
