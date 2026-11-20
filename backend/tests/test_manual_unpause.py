import pytest
from community.models import WhatsAppLinkConfig
from django.utils import timezone
from users.models import MembershipStatus, User

EMAIL = "paused@example.com"
GUIDELINES = {"membership_status": MembershipStatus.GUIDELINES_PAUSED}
ATTENDANCE = {
    "attendance_paused_at": timezone.now(),
    "membership_status": MembershipStatus.ATTENDANCE_PAUSED,
}


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
    def test_lifting_a_guidelines_pause_emails_and_stamps(self, patch_user, fake_email_sender):
        WhatsAppLinkConfig.objects.update_or_create(pk=1, defaults={"link": "https://wa.example"})
        user = _member(has_joined_whatsapp=True, **GUIDELINES)
        response = patch_user(user, {"guidelines_paused": False})
        assert response.json()["unpaused_at"] is not None
        assert user.unpaused_at is not None
        assert user.membership_status == MembershipStatus.ATTENDANCE_PAUSED
        assert user.has_joined_whatsapp is False
        [sent] = _sends(fake_email_sender)
        assert "official or club event" in sent["text"]
        assert "/calendar" in sent["html"]
        assert "wa.example" not in sent["text"] + sent["html"]

    @pytest.mark.parametrize(
        ("pause", "payload"),
        [
            ({}, {"guidelines_paused": True}),
            ({}, {"first_name": "Sam"}),
            (GUIDELINES, {"first_name": "Sam"}),
            (ATTENDANCE, {"first_name": "Sam"}),
        ],
        ids=["pausing", "never_paused", "still_guidelines_paused", "still_attendance_paused"],
    )
    def test_no_email_or_stamp_without_lifting_a_guidelines_pause(
        self, patch_user, fake_email_sender, pause, payload
    ):
        user = _member(**pause)
        patch_user(user, payload)
        assert user.unpaused_at is None
        assert _sends(fake_email_sender) == []

    @pytest.mark.parametrize(
        "payload",
        [{"guidelines_paused": True}, {"attendance_paused": True}],
        ids=["guidelines", "attendance"],
    )
    def test_a_new_pause_clears_the_stamp(self, patch_user, fake_email_sender, payload):
        user = _member(unpaused_at=timezone.now())
        patch_user(user, payload)
        assert user.unpaused_at is None

    def test_member_without_email_is_stamped_but_not_emailed(self, patch_user, fake_email_sender):
        user = _member(**GUIDELINES, email="")
        patch_user(user, {"guidelines_paused": False})
        assert user.unpaused_at is not None
        fake_email_sender.send.assert_not_called()

    def test_send_error_does_not_fail_the_unpause(self, patch_user, fake_email_sender):
        fake_email_sender.send.side_effect = RuntimeError("provider down")
        user = _member(**GUIDELINES)
        assert patch_user(user, {"guidelines_paused": False}).status_code == 200
        assert user.is_guidelines_paused is False

    def test_lifting_an_attendance_pause_is_refused(self, patch_user, fake_email_sender):
        user = _member(**ATTENDANCE)
        response = patch_user(user, {"attendance_paused": False})
        assert response.status_code == 400
        assert response.json()["detail"][0]["code"] == "user.attendance_pause_lifts_on_check_in"
        assert user.membership_status == MembershipStatus.ATTENDANCE_PAUSED
        assert user.unpaused_at is None
        assert _sends(fake_email_sender) == []
