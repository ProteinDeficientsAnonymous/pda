"""Tests for the unauthenticated request-login-link endpoint."""

import pytest
from notifications.models import Notification, NotificationType
from users.permissions import PermissionKey
from users.roles import Role


def _make_approver():
    """Create a user with APPROVE_JOIN_REQUESTS permission and return them."""
    from users.models import User

    approver = User.objects.create_user(
        phone_number="+12025559001", password="pass", display_name="Approver"
    )
    role = Role.objects.create(name="vetter", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS])
    approver.roles.add(role)
    return approver


_URL = "/api/community/request-login-link/"
_PHONE = "+12025558800"


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestRequestLoginLink:
    def test_returns_200_for_existing_user(self, api_client):
        from users.models import User

        User.objects.create_user(phone_number=_PHONE, password="pass", display_name="Invited")
        response = api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")
        assert response.status_code == 200

    def test_returns_200_for_unknown_phone(self, api_client):
        """Always returns 200 regardless of whether phone exists (anti-enumeration).

        Unknown phones get the admin-fallback response shape so the response
        doesn't reveal "no account" vs "account with no email".
        """
        response = api_client.post(
            _URL, {"phone_number": "+12025559999"}, content_type="application/json"
        )
        assert response.status_code == 200
        assert response.json()["delivery"] == "admin"

    def test_returns_200_for_invalid_phone(self, api_client):
        response = api_client.post(
            _URL, {"phone_number": "not-a-phone"}, content_type="application/json"
        )
        assert response.status_code == 200

    def test_creates_magic_token_for_existing_user(self, api_client):
        from users.models import MagicLoginToken, User

        user = User.objects.create_user(phone_number=_PHONE, password="pass")
        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")
        assert MagicLoginToken.objects.filter(user=user).exists()

    def test_self_service_token_requires_password_reset(self, api_client):
        """Self-service login-link tokens must be flagged so consuming forces a reset."""
        from users.models import MagicLoginToken, User

        user = User.objects.create_user(phone_number=_PHONE, password="pass")
        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")
        token = MagicLoginToken.objects.filter(user=user).latest("created_at")
        assert token.requires_password_reset is True

    def test_does_not_create_token_for_unknown_phone(self, api_client):
        from users.models import MagicLoginToken

        api_client.post(_URL, {"phone_number": "+12025559998"}, content_type="application/json")
        assert MagicLoginToken.objects.count() == 0

    def test_creates_notification_for_approvers(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number=_PHONE, password="pass", display_name="Invited Person"
        )
        approver = User.objects.create_user(
            phone_number="+12025559001", password="pass", display_name="Approver"
        )
        role = Role.objects.create(name="vetter", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS])
        approver.roles.add(role)

        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")

        notif = Notification.objects.get(recipient=approver)
        assert notif.notification_type == NotificationType.MAGIC_LINK_REQUEST
        assert user.display_name in notif.message
        assert notif.related_user_id == user.pk  # ty: ignore[unresolved-attribute]
        assert "token" not in notif.message.lower()

    def test_does_not_create_notification_for_unknown_phone(self, api_client):
        from users.models import User

        approver = User.objects.create_user(phone_number="+12025559001", password="pass")
        role = Role.objects.create(name="vetter", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS])
        approver.roles.add(role)

        api_client.post(_URL, {"phone_number": "+12025559999"}, content_type="application/json")

        assert not Notification.objects.filter(recipient=approver).exists()

    def test_rate_limit_prevents_duplicate_tokens_within_cooldown(self, api_client):
        from users.models import MagicLoginToken, User

        user = User.objects.create_user(phone_number=_PHONE, password="pass")
        # First request
        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")
        count_after_first = MagicLoginToken.objects.filter(user=user).count()
        assert count_after_first == 1

        # Second request within the cooldown window — should NOT create another token
        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")
        assert MagicLoginToken.objects.filter(user=user).count() == count_after_first

    def test_login_link_requested_does_not_block_re_request(self, api_client):
        """A prior pending request must NOT block a fresh request (no recent token)."""
        from users.models import MagicLoginToken, User

        user = User.objects.create_user(phone_number=_PHONE, password="pass")
        user.login_link_requested = True
        user.save(update_fields=["login_link_requested"])

        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")

        # A new token is minted despite login_link_requested already being set.
        assert MagicLoginToken.objects.filter(user=user).count() == 1

    def test_recent_token_returns_cooldown(self, api_client):
        """A second request within the cooldown window returns cooldown, mints no token."""
        from users.models import MagicLoginToken, User

        user = User.objects.create_user(phone_number=_PHONE, password="pass")
        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")
        assert MagicLoginToken.objects.filter(user=user).count() == 1

        resp = api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json()["delivery"] == "cooldown"
        # No second token created during the cooldown window.
        assert MagicLoginToken.objects.filter(user=user).count() == 1

    def test_new_request_invalidates_prior_unused_token(self, api_client):
        """Outside the cooldown, a fresh request invalidates the previous unused link."""
        from datetime import timedelta

        from django.utils import timezone
        from users.models import MagicLoginToken, User

        user = User.objects.create_user(phone_number=_PHONE, password="pass")
        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")
        old = MagicLoginToken.objects.get(user=user)
        # Push the old token outside the cooldown window.
        MagicLoginToken.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(minutes=10)
        )

        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")

        old.refresh_from_db()
        assert old.used is True  # prior link invalidated
        # The newest unused token is the only valid one.
        assert MagicLoginToken.objects.filter(user=user, used=False).count() == 1

    def test_sets_login_link_requested_flag(self, api_client):
        from users.models import User

        user = User.objects.create_user(phone_number=_PHONE, password="pass")
        assert user.login_link_requested is False

        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")

        user.refresh_from_db()
        assert user.login_link_requested is True

    def test_rate_limited_after_five_requests_per_minute(self, api_client):
        from django.core.cache import cache

        cache.clear()
        for _ in range(5):
            resp = api_client.post(
                _URL,
                {"phone_number": "+15005550000"},
                content_type="application/json",
            )
            assert resp.status_code == 200
        resp = api_client.post(
            _URL,
            {"phone_number": "+15005550000"},
            content_type="application/json",
        )
        assert resp.status_code == 429
        assert resp.json()["detail"][0]["code"] == "rate.limited"
        cache.clear()


@pytest.mark.django_db
class TestRequestLoginLinkEmailDelivery:
    def test_user_with_email_send_succeeds(self, api_client, fake_email_sender):
        from users.models import User

        User.objects.create_user(
            phone_number="+12025550101",
            display_name="Sam",
            email="sam@example.com",
        )
        resp = api_client.post(
            "/api/community/request-login-link/",
            data={"phone_number": "+12025550101"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["delivery"] == "email"
        assert "email on file" in resp.json()["detail"]
        fake_email_sender.send.assert_called_once()
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == "sam@example.com"

    def test_email_path_does_not_set_login_link_requested(self, api_client, fake_email_sender):
        """Email success must leave login_link_requested False so re-requests stay open."""
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550101",
            display_name="Sam",
            email="sam@example.com",
        )
        api_client.post(
            "/api/community/request-login-link/",
            data={"phone_number": "+12025550101"},
            content_type="application/json",
        )
        user.refresh_from_db()
        assert user.login_link_requested is False

    def test_admin_fallback_sets_login_link_requested(self, api_client, fake_email_sender):
        """No-email fallback dedupes admin notifications via login_link_requested."""
        from users.models import User

        _make_approver()
        user = User.objects.create_user(
            phone_number="+12025550102",
            display_name="NoEmail",
            email=None,
        )
        api_client.post(
            "/api/community/request-login-link/",
            data={"phone_number": "+12025550102"},
            content_type="application/json",
        )
        user.refresh_from_db()
        assert user.login_link_requested is True

    def test_user_with_email_send_succeeds_skips_admin_notification(
        self, api_client, fake_email_sender
    ):
        from users.models import User

        approver = _make_approver()
        user = User.objects.create_user(
            phone_number="+12025550101",
            display_name="Sam",
            email="sam@example.com",
        )
        api_client.post(
            "/api/community/request-login-link/",
            data={"phone_number": "+12025550101"},
            content_type="application/json",
        )
        # Email sent successfully — admin notification must NOT fire
        fake_email_sender.send.assert_called_once()
        assert not Notification.objects.filter(
            recipient=approver,
            notification_type=NotificationType.MAGIC_LINK_REQUEST,
            related_user=user,
        ).exists()

    def test_user_with_email_send_fails_still_returns_200(self, api_client, fake_email_sender):
        from notifications.email_sender import SendResult
        from users.models import User

        fake_email_sender.send.return_value = SendResult(success=False, error="invalid recipient")
        approver = _make_approver()
        user = User.objects.create_user(
            phone_number="+12025550101",
            display_name="Sam",
            email="bad@example.com",
        )
        resp = api_client.post(
            "/api/community/request-login-link/",
            data={"phone_number": "+12025550101"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        fake_email_sender.send.assert_called_once()
        # Admin notification fallback SHOULD fire on email send failure
        notif = Notification.objects.get(
            recipient=approver, notification_type=NotificationType.MAGIC_LINK_REQUEST
        )
        assert notif.related_user_id == user.pk  # ty: ignore[unresolved-attribute]

    def test_user_with_no_email_skips_send(self, api_client, fake_email_sender):
        from users.models import User

        approver = _make_approver()
        user = User.objects.create_user(
            phone_number="+12025550101",
            display_name="Sam",
            email=None,
        )
        resp = api_client.post(
            "/api/community/request-login-link/",
            data={"phone_number": "+12025550101"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["delivery"] == "admin"
        assert "admin will follow up" in resp.json()["detail"]
        fake_email_sender.send.assert_not_called()
        # Admin notification still fires — no-email path is unchanged
        notif = Notification.objects.get(
            recipient=approver, notification_type=NotificationType.MAGIC_LINK_REQUEST
        )
        assert notif.related_user_id == user.pk  # ty: ignore[unresolved-attribute]

    def test_unexpected_email_error_falls_through(self, api_client, fake_email_sender):
        """If something unexpected raises inside the email branch (template missing,
        bug in helper, etc.), the endpoint still returns 200 and the admin
        notification fallback fires."""
        from users.models import User

        fake_email_sender.send.side_effect = RuntimeError("unexpected boom")
        approver = _make_approver()
        user = User.objects.create_user(
            phone_number="+12025550101",
            display_name="Sam",
            email="sam@example.com",
        )
        resp = api_client.post(
            "/api/community/request-login-link/",
            data={"phone_number": "+12025550101"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        # Admin notification fallback should have fired
        notif = Notification.objects.get(
            recipient=approver, notification_type=NotificationType.MAGIC_LINK_REQUEST
        )
        assert notif.related_user_id == user.pk  # ty: ignore[unresolved-attribute]
