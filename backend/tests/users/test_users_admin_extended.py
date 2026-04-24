"""Tests for user update, profile, delete, and magic link."""

import pytest
from community._validation import Code
from tests._asserts import assert_error_code


@pytest.mark.django_db
class TestUpdateUser:
    def test_update_user_not_found(self, api_client, manage_users_headers):
        response = api_client.patch(
            "/api/auth/users/00000000-0000-0000-0000-000000000000/",
            {"display_name": "Ghost"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 404
        assert_error_code(response, Code.User.NOT_FOUND)

    def test_update_user_duplicate_phone(
        self, api_client, manage_users_headers, test_user, other_user
    ):
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/",
            {"phone_number": test_user.phone_number},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 409
        assert_error_code(response, Code.Phone.ALREADY_EXISTS, "phone_number")

    def test_update_user_invalid_phone(self, api_client, manage_users_headers, other_user):
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/",
            {"phone_number": "not-a-phone"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Phone.INVALID, "phone_number")

    def test_update_user_pause(self, api_client, manage_users_headers, other_user):
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/",
            {"is_paused": True},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 200
        other_user.refresh_from_db()
        assert other_user.is_paused is True

    def test_update_user_requires_auth(self, api_client, other_user):
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/",
            {"display_name": "Hacker"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_update_user_requires_permission(self, api_client, auth_headers, other_user):
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/",
            {"display_name": "Blocked"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_cannot_pause_own_account(self, api_client, manage_users_headers, manage_users_user):
        response = api_client.patch(
            f"/api/auth/users/{manage_users_user.pk}/",
            {"is_paused": True},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 400

    def test_cannot_pause_admin(self, api_client, manage_users_headers, other_user):
        from users.roles import Role

        admin_role = Role.objects.get(name="admin", is_default=True)
        other_user.roles.add(admin_role)
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/",
            {"is_paused": True},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.User.CANNOT_PAUSE_ADMIN)
        other_user.refresh_from_db()
        assert other_user.is_paused is False

    def test_admin_list_includes_paused_users(self, api_client, manage_users_headers, other_user):
        other_user.is_paused = True
        other_user.save(update_fields=["is_paused"])
        response = api_client.get("/api/auth/users/", **manage_users_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) in ids


@pytest.mark.django_db
class TestMemberProfile:
    def test_member_profile_returns_404_for_paused_user(self, api_client, auth_headers, other_user):
        other_user.is_paused = True
        other_user.save(update_fields=["is_paused"])
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 404


@pytest.mark.django_db
class TestDeleteUser:
    def test_delete_user_not_found(self, api_client, manage_users_headers):
        response = api_client.delete(
            "/api/auth/users/00000000-0000-0000-0000-000000000000/",
            **manage_users_headers,
        )
        assert response.status_code == 404
        assert_error_code(response, Code.User.NOT_FOUND)

    def test_delete_user_requires_auth(self, api_client, other_user):
        response = api_client.delete(f"/api/auth/users/{other_user.pk}/")
        assert response.status_code == 401

    def test_delete_user_requires_permission(self, api_client, auth_headers, other_user):
        response = api_client.delete(
            f"/api/auth/users/{other_user.pk}/",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_delete_user_soft_archives(self, api_client, manage_users_headers, other_user):
        from users.models import User

        response = api_client.delete(
            f"/api/auth/users/{other_user.pk}/",
            **manage_users_headers,
        )
        assert response.status_code == 204
        refreshed = User.objects.get(pk=other_user.pk)
        assert refreshed.archived_at is not None

    def test_delete_user_already_archived_returns_400(
        self, api_client, manage_users_headers, other_user
    ):
        from django.utils import timezone

        other_user.archived_at = timezone.now()
        other_user.save(update_fields=["archived_at"])

        response = api_client.delete(
            f"/api/auth/users/{other_user.pk}/",
            **manage_users_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.User.ALREADY_ARCHIVED)

    def test_archived_user_excluded_from_list(self, api_client, manage_users_headers, other_user):
        from django.utils import timezone

        other_user.archived_at = timezone.now()
        other_user.save(update_fields=["archived_at"])

        response = api_client.get("/api/auth/users/", **manage_users_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids

    def test_archived_user_excluded_from_search(self, api_client, manage_users_headers, other_user):
        from django.utils import timezone

        other_user.archived_at = timezone.now()
        other_user.save(update_fields=["archived_at"])

        response = api_client.get("/api/auth/users/search/?q=Other", **manage_users_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids

    def test_archived_user_cannot_login(self, api_client, other_user):
        from django.utils import timezone

        other_user.archived_at = timezone.now()
        other_user.save(update_fields=["archived_at"])

        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": other_user.phone_number, "password": "otherpass123"},
            content_type="application/json",
        )
        assert response.status_code == 403
        assert_error_code(response, Code.Auth.ACCOUNT_ARCHIVED)

    def test_archived_user_cannot_magic_login(self, api_client, other_user):
        from django.utils import timezone
        from users.models import MagicLoginToken

        magic = MagicLoginToken.create_for_user(other_user)
        other_user.archived_at = timezone.now()
        other_user.save(update_fields=["archived_at"])

        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 403
        assert_error_code(response, Code.Auth.ACCOUNT_ARCHIVED)


@pytest.mark.django_db
class TestGenerateMagicLink:
    def test_generate_magic_link_success(self, api_client, manage_users_headers, other_user):
        response = api_client.post(
            f"/api/auth/users/{other_user.pk}/magic-link/",
            **manage_users_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["magic_link_token"]) == 36

    def test_generate_magic_link_sets_needs_onboarding(
        self, api_client, manage_users_headers, other_user
    ):
        other_user.needs_onboarding = False
        other_user.save(update_fields=["needs_onboarding"])
        response = api_client.post(
            f"/api/auth/users/{other_user.pk}/magic-link/",
            **manage_users_headers,
        )
        assert response.status_code == 200
        other_user.refresh_from_db()
        assert other_user.needs_onboarding
        assert not other_user.has_usable_password()

    def test_generate_magic_link_not_found(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/users/00000000-0000-0000-0000-000000000000/magic-link/",
            **manage_users_headers,
        )
        assert response.status_code == 404

    def test_generate_magic_link_requires_permission(self, api_client, auth_headers, other_user):
        response = api_client.post(
            f"/api/auth/users/{other_user.pk}/magic-link/",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_generate_magic_link_reuses_recent_token(
        self, api_client, manage_users_headers, other_user
    ):
        """Two admins clicking generate within 5 min get the same token (no duplicate)."""
        first = api_client.post(
            f"/api/auth/users/{other_user.pk}/magic-link/",
            **manage_users_headers,
        )
        assert first.status_code == 200
        first_token = first.json()["magic_link_token"]

        second = api_client.post(
            f"/api/auth/users/{other_user.pk}/magic-link/",
            **manage_users_headers,
        )
        assert second.status_code == 200
        assert second.json()["magic_link_token"] == first_token
        assert "already" in second.json()["detail"].lower()

    def test_generate_magic_link_clears_request_notifications(
        self, api_client, manage_users_headers, other_user
    ):
        """When admin generates the link, MAGIC_LINK_REQUEST notifications are marked read."""
        from notifications.models import Notification, NotificationType
        from users.models import User

        approver = User.objects.create_user(phone_number="+12025557788", password="pass")
        Notification.objects.create(
            recipient=approver,
            notification_type=NotificationType.MAGIC_LINK_REQUEST,
            related_user=other_user,
            message="link request",
        )
        other_user.login_link_requested = True
        other_user.save(update_fields=["login_link_requested"])

        response = api_client.post(
            f"/api/auth/users/{other_user.pk}/magic-link/",
            **manage_users_headers,
        )
        assert response.status_code == 200
        notif = Notification.objects.get(recipient=approver, related_user=other_user)
        assert notif.is_read is True
        other_user.refresh_from_db()
        assert other_user.login_link_requested is False
