import pytest
from community.models import WhatsAppLinkConfig
from django.utils import timezone
from users.models import User

EMAIL = "paused@example.com"
GUIDELINES = {"is_paused": True}
ATTENDANCE = {"attendance_paused_at": timezone.now(), "is_member": False}


@pytest.fixture
def patch_user(api_client, manage_users_headers, django_capture_on_commit_callbacks):
    def patch(user: User, payload: dict):
        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.patch(
                f"/api/auth/users/{user.pk}/",
                payload,
                content_type="application/json",
                **manage_users_headers,
            )
        user.refresh_from_db()
        return response

    return patch


def _member(**extra) -> User:
    extra.setdefault("email", EMAIL)
    return User.objects.create_user(phone_number="+12025550199", first_name="Pat", **extra)


def _sends(fake_email_sender) -> list[dict]:
    return [c.kwargs for c in fake_email_sender.send.call_args_list if c.kwargs["to"] == EMAIL]


@pytest.mark.django_db
class TestManualUnpause:
    @pytest.mark.parametrize(
        ("pause", "payload"),
        [(GUIDELINES, {"is_paused": False}), (ATTENDANCE, {"attendance_paused": False})],
        ids=["guidelines", "attendance"],
    )
    def test_lifting_the_last_pause_emails_without_the_link(
        self, patch_user, fake_email_sender, pause, payload
    ):
        WhatsAppLinkConfig.objects.update_or_create(pk=1, defaults={"link": "https://wa.example"})
        patch_user(_member(**pause), payload)
        [sent] = _sends(fake_email_sender)
        assert "official or club event" in sent["text"]
        assert "/calendar" in sent["html"]
        assert "wa.example" not in sent["text"] + sent["html"]

    @pytest.mark.parametrize(
        ("pause", "payload"),
        [
            ({}, {"is_paused": True}),
            ({}, {"first_name": "Sam"}),
            (GUIDELINES, {"first_name": "Sam"}),
            (GUIDELINES, {"is_paused": False, "attendance_paused": True}),
            ({**GUIDELINES, **ATTENDANCE}, {"is_paused": False}),
            ({**GUIDELINES, **ATTENDANCE}, {"attendance_paused": False}),
        ],
        ids=[
            "pausing",
            "never_paused",
            "still_paused",
            "into_attendance_pause",
            "attendance_pause_remains",
            "guidelines_pause_remains",
        ],
    )
    def test_no_email_while_a_pause_remains(self, patch_user, fake_email_sender, pause, payload):
        patch_user(_member(**pause), payload)
        assert _sends(fake_email_sender) == []

    @pytest.mark.parametrize(
        "extra", [{"archived_at": timezone.now()}, {"email": ""}], ids=["archived", "no_email"]
    )
    def test_ineligible_member_is_not_emailed(self, patch_user, fake_email_sender, extra):
        patch_user(_member(**GUIDELINES, **extra), {"is_paused": False})
        fake_email_sender.send.assert_not_called()

    def test_send_error_does_not_fail_the_unpause(self, patch_user, fake_email_sender):
        fake_email_sender.send.side_effect = RuntimeError("provider down")
        user = _member(**GUIDELINES)
        assert patch_user(user, {"is_paused": False}).status_code == 200
        assert not user.is_paused
