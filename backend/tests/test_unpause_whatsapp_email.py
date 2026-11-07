import pytest
from community.models import WhatsAppLinkConfig
from users.models import User

LINK = "https://chat.whatsapp.com/abc123"
EMAIL = "paused@example.com"


@pytest.fixture
def whatsapp_link(db):
    config = WhatsAppLinkConfig.get()
    config.link = LINK
    config.save()


@pytest.fixture
def patch_user(api_client, manage_users_headers, django_capture_on_commit_callbacks):
    def patch(user: User, payload: dict):
        with django_capture_on_commit_callbacks(execute=True):
            return api_client.patch(
                f"/api/auth/users/{user.pk}/",
                payload,
                content_type="application/json",
                **manage_users_headers,
            )

    return patch


def _member(*, is_paused: bool, email: str = EMAIL) -> User:
    return User.objects.create_user(
        phone_number="+12025550199", first_name="Pat", email=email, is_paused=is_paused
    )


def _sends(fake_email_sender) -> list[dict]:
    return [c.kwargs for c in fake_email_sender.send.call_args_list if c.kwargs["to"] == EMAIL]


@pytest.mark.django_db
@pytest.mark.usefixtures("whatsapp_link")
class TestMemberAdminUnpause:
    def test_unpausing_emails_the_whatsapp_link(self, patch_user, fake_email_sender):
        response = patch_user(_member(is_paused=True), {"is_paused": False})
        assert response.status_code == 200
        [sent] = _sends(fake_email_sender)
        assert LINK in sent["text"]
        assert f'href="{LINK}"' in sent["html"]

    @pytest.mark.parametrize(
        ("was_paused", "payload"),
        [(False, {"is_paused": True}), (False, {"first_name": "Sam"}), (True, {"is_paused": True})],
        ids=["pausing", "never_paused", "still_paused"],
    )
    def test_no_email_unless_pause_is_lifted(
        self, patch_user, fake_email_sender, was_paused, payload
    ):
        patch_user(_member(is_paused=was_paused), payload)
        assert _sends(fake_email_sender) == []

    def test_failed_email_keeps_the_unpause(self, patch_user, fake_email_sender):
        fake_email_sender.send.side_effect = RuntimeError("provider down")
        user = _member(is_paused=True)
        response = patch_user(user, {"is_paused": False})
        assert response.status_code == 200
        user.refresh_from_db()
        assert not user.is_paused

    def test_member_without_email_is_skipped(self, patch_user, fake_email_sender):
        patch_user(_member(is_paused=True, email=""), {"is_paused": False})
        fake_email_sender.send.assert_not_called()


@pytest.mark.django_db
def test_no_email_when_no_link_is_configured(patch_user, fake_email_sender):
    patch_user(_member(is_paused=True), {"is_paused": False})
    assert _sends(fake_email_sender) == []
