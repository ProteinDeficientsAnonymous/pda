import json

import pytest
from community.models import Event, EventStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso

CREATE_EVENT_URL = "/api/community/events/"


def _make_user(phone: str, name: str = "Member", email: str | None = "") -> User:
    return User.objects.create_user(
        phone_number=phone,
        password="testpass123",
        first_name=name,
        email=email,
    )


def _auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def _create_event_via_api(api_client, creator: User, co_host_ids: list[str]) -> dict:
    payload = {
        "title": "Community Potluck",
        "start_datetime": future_iso(days=30),
        "end_datetime": future_iso(days=30, hours=2),
        "status": EventStatus.ACTIVE,
        "co_host_ids": co_host_ids,
    }
    response = api_client.post(
        CREATE_EVENT_URL,
        data=json.dumps(payload),
        content_type="application/json",
        **_auth_headers(creator),
    )
    assert response.status_code == 201, response.content
    return response.json()


@pytest.fixture
def creator(db) -> User:
    return _make_user("+12025550111", "Creator", email="creator@example.com")


@pytest.mark.django_db
class TestCohostInviteEmail:
    def test_sends_email_when_invitee_has_email(self, api_client, creator, fake_email_sender):
        invitee = _make_user("+12025550112", "Invitee", email="invitee@example.com")

        _create_event_via_api(api_client, creator, co_host_ids=[str(invitee.pk)])

        fake_email_sender.send.assert_called_once()
        call_kwargs = fake_email_sender.send.call_args.kwargs
        assert call_kwargs["to"] == "invitee@example.com"
        assert "co-host" in call_kwargs["subject"]
        assert call_kwargs["subject"] == call_kwargs["subject"].lower()
        assert "community potluck" in call_kwargs["text"].lower()
        assert "creator" in call_kwargs["text"].lower()

    def test_no_email_attempted_when_invitee_has_no_email(
        self, api_client, creator, fake_email_sender
    ):
        invitee = _make_user("+12025550113", "Invitee", email="")

        response_data = _create_event_via_api(api_client, creator, co_host_ids=[str(invitee.pk)])

        fake_email_sender.send.assert_not_called()
        # Invite flow itself still succeeds — email is best-effort, not required.
        assert response_data["id"]

    def test_does_not_crash_when_send_fails(self, api_client, creator, fake_email_sender):
        from notifications.email_sender import SendResult

        fake_email_sender.send.side_effect = Exception("smtp exploded")
        invitee = _make_user("+12025550114", "Invitee", email="invitee2@example.com")

        response = api_client.post(
            CREATE_EVENT_URL,
            data=json.dumps(
                {
                    "title": "Community Potluck",
                    "start_datetime": future_iso(days=30),
                    "end_datetime": future_iso(days=30, hours=2),
                    "status": EventStatus.ACTIVE,
                    "co_host_ids": [str(invitee.pk)],
                }
            ),
            content_type="application/json",
            **_auth_headers(creator),
        )

        assert response.status_code == 201, response.content
        fake_email_sender.send.side_effect = None
        fake_email_sender.send.return_value = SendResult(success=True)

    def test_no_email_sent_to_inviter_for_self_invite(self, api_client, creator, fake_email_sender):
        _create_event_via_api(api_client, creator, co_host_ids=[str(creator.pk)])
        fake_email_sender.send.assert_not_called()

    def test_email_via_patch_adds_new_cohost(self, api_client, creator, fake_email_sender):
        data = _create_event_via_api(api_client, creator, co_host_ids=[])
        event_id = data["id"]
        invitee = _make_user("+12025550115", "Invitee", email="patched@example.com")

        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"co_host_ids": [str(invitee.pk)]}),
            content_type="application/json",
            **_auth_headers(creator),
        )

        assert response.status_code == 200, response.content
        fake_email_sender.send.assert_called_once()
        assert fake_email_sender.send.call_args.kwargs["to"] == "patched@example.com"

    def test_event_url_points_to_event_detail_page(self, api_client, creator, fake_email_sender):
        invitee = _make_user("+12025550116", "Invitee", email="invitee3@example.com")
        data = _create_event_via_api(api_client, creator, co_host_ids=[str(invitee.pk)])
        event = Event.objects.get(id=data["id"])

        call_kwargs = fake_email_sender.send.call_args.kwargs
        assert f"/events/{event.pk}" in call_kwargs["text"]
        assert f"/events/{event.pk}" in call_kwargs["html"]
