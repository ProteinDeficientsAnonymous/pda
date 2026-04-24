"""Tests for the unauthenticated request-login-link endpoint."""

import pytest
from notifications.models import Notification, NotificationType
from users.permissions import PermissionKey
from users.roles import Role

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
        """Always returns 200 regardless of whether phone exists (anti-enumeration)."""
        response = api_client.post(
            _URL, {"phone_number": "+12025559999"}, content_type="application/json"
        )
        assert response.status_code == 200

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

    def test_rate_limit_prevents_duplicate_tokens_within_5_minutes(self, api_client):
        from users.models import MagicLoginToken, User

        user = User.objects.create_user(phone_number=_PHONE, password="pass")
        # First request
        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")
        count_after_first = MagicLoginToken.objects.filter(user=user).count()
        assert count_after_first == 1

        # Second request within 5 minutes — should NOT create another token
        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")
        assert MagicLoginToken.objects.filter(user=user).count() == count_after_first

    def test_skips_when_login_link_already_requested(self, api_client):
        """Spam-tap: subsequent requests are no-ops while a request is pending."""
        from users.models import User

        approver = User.objects.create_user(phone_number="+12025559001", password="pass")
        role = Role.objects.create(name="vetter", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS])
        approver.roles.add(role)
        user = User.objects.create_user(phone_number=_PHONE, password="pass")
        user.login_link_requested = True
        user.save(update_fields=["login_link_requested"])

        api_client.post(_URL, {"phone_number": _PHONE}, content_type="application/json")

        # No new notification should be created — existing pending request is respected.
        assert not Notification.objects.filter(recipient=approver, related_user=user).exists()

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
