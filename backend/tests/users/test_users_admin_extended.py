"""Tests for user update, profile, delete, and magic link."""

import logging

import pytest
from community._validation import Code
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from tests._asserts import assert_error_code
from users.models import MagicLoginToken, User
from users.roles import Role


def _capture_audit(caplog):
    """Attach caplog's handler to the non-propagating pda.audit logger.

    pda.audit has propagate=False (see settings LOGGING), so caplog's root
    handler never sees its records. Attaching the handler directly captures them.
    """
    audit_logger = logging.getLogger("pda.audit")
    audit_logger.addHandler(caplog.handler)
    return audit_logger


@pytest.mark.django_db
class TestUpdateUser:
    def test_update_user_not_found(self, api_client, manage_users_headers):
        response = api_client.patch(
            "/api/auth/users/00000000-0000-0000-0000-000000000000/",
            {"first_name": "Ghost"},
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

    def test_pause_strips_non_member_roles(
        self, api_client, manage_users_headers, other_user, caplog
    ):
        member_role = Role.objects.get(name="member", is_default=True)
        extra_role = Role.objects.create(name="organizer")
        other_user.roles.add(member_role, extra_role)
        audit_logger = _capture_audit(caplog)
        try:
            with caplog.at_level(logging.WARNING, logger="pda.audit"):
                response = api_client.patch(
                    f"/api/auth/users/{other_user.pk}/",
                    {"is_paused": True},
                    content_type="application/json",
                    **manage_users_headers,
                )
        finally:
            audit_logger.removeHandler(caplog.handler)
        assert response.status_code == 200
        role_names = set(other_user.roles.values_list("name", flat=True))
        assert role_names == {"member"}
        paused_logs = [r for r in caplog.records if getattr(r, "action", None) == "user_paused"]
        assert len(paused_logs) == 1
        assert paused_logs[0].details == {"removed_role_ids": [str(extra_role.id)]}

    def test_pause_member_only_is_noop_for_roles(
        self, api_client, manage_users_headers, other_user, caplog
    ):
        member_role = Role.objects.get(name="member", is_default=True)
        other_user.roles.add(member_role)
        audit_logger = _capture_audit(caplog)
        try:
            with caplog.at_level(logging.WARNING, logger="pda.audit"):
                response = api_client.patch(
                    f"/api/auth/users/{other_user.pk}/",
                    {"is_paused": True},
                    content_type="application/json",
                    **manage_users_headers,
                )
        finally:
            audit_logger.removeHandler(caplog.handler)
        assert response.status_code == 200
        role_names = set(other_user.roles.values_list("name", flat=True))
        assert role_names == {"member"}
        paused_logs = [r for r in caplog.records if getattr(r, "action", None) == "user_paused"]
        assert len(paused_logs) == 1
        assert paused_logs[0].details == {"removed_role_ids": []}

    def test_unpause_does_not_restore_roles(self, api_client, manage_users_headers, other_user):
        member_role = Role.objects.get(name="member", is_default=True)
        extra_role = Role.objects.create(name="organizer")
        other_user.roles.add(member_role, extra_role)
        other_user.is_paused = True
        other_user.roles.remove(extra_role)
        other_user.save(update_fields=["is_paused"])
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/",
            {"is_paused": False},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 200
        other_user.refresh_from_db()
        assert other_user.is_paused is False
        role_names = set(other_user.roles.values_list("name", flat=True))
        assert role_names == {"member"}

    def test_update_user_requires_auth(self, api_client, other_user):
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/",
            {"first_name": "Hacker"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_update_user_requires_permission(self, api_client, auth_headers, other_user):
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/",
            {"first_name": "Blocked"},
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

    def test_admin_list_excludes_non_members(self, api_client, manage_users_headers, other_user):
        other_user.is_member = False
        other_user.save(update_fields=["is_member"])
        response = api_client.get("/api/auth/users/", **manage_users_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids

    def test_admin_list_includes_non_members_when_opted_in(
        self, api_client, manage_users_headers, other_user
    ):
        other_user.is_member = False
        other_user.save(update_fields=["is_member"])
        response = api_client.get(
            "/api/auth/users/?include_non_members=true", **manage_users_headers
        )
        assert response.status_code == 200
        rows = {u["id"]: u for u in response.json()}
        assert str(other_user.pk) in rows
        assert rows[str(other_user.pk)]["is_member"] is False

    def test_admin_update_non_member_returns_404(
        self, api_client, manage_users_headers, other_user
    ):
        other_user.is_member = False
        other_user.save(update_fields=["is_member"])
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/",
            {"first_name": "Renamed"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestMemberProfile:
    def test_member_profile_returns_404_for_paused_user(self, api_client, auth_headers, other_user):
        other_user.is_paused = True
        other_user.save(update_fields=["is_paused"])
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 404

    def test_member_profile_returns_404_for_non_member(self, api_client, auth_headers, other_user):
        other_user.is_member = False
        other_user.save(update_fields=["is_member"])
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 404

    def test_member_profile_returns_404_for_onboarding_pending_user(
        self, api_client, auth_headers, other_user
    ):
        other_user.needs_onboarding = True
        other_user.save(update_fields=["needs_onboarding"])
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 404

    def test_member_profile_returns_pronouns(self, api_client, auth_headers, other_user):
        other_user.pronouns = "they/them"
        other_user.save(update_fields=["pronouns"])
        response = api_client.get(f"/api/auth/users/{other_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["pronouns"] == "they/them"


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
        other_user.archived_at = timezone.now()
        other_user.save(update_fields=["archived_at"])

        response = api_client.delete(
            f"/api/auth/users/{other_user.pk}/",
            **manage_users_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.User.ALREADY_ARCHIVED)

    def test_archived_user_excluded_from_list(self, api_client, manage_users_headers, other_user):
        other_user.archived_at = timezone.now()
        other_user.save(update_fields=["archived_at"])

        response = api_client.get("/api/auth/users/", **manage_users_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids

    def test_archived_user_excluded_from_search(self, api_client, manage_users_headers, other_user):
        other_user.archived_at = timezone.now()
        other_user.save(update_fields=["archived_at"])

        response = api_client.get("/api/auth/users/search/?q=Other", **manage_users_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids

    def test_onboarding_pending_user_excluded_from_search(
        self, api_client, manage_users_headers, other_user
    ):
        other_user.needs_onboarding = True
        other_user.save(update_fields=["needs_onboarding"])

        response = api_client.get("/api/auth/users/search/?q=Other", **manage_users_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(other_user.pk) not in ids

    def test_archived_user_cannot_login(self, api_client, other_user):
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


@pytest.mark.django_db
class TestSearchUsersRespectsShowPhone:
    """Issue 452 — search_users must honor the per-user show_phone flag."""

    def _find(self, response, user_id):
        return next(u for u in response.json() if u["id"] == str(user_id))

    def test_phone_shown_when_show_phone_true(self, api_client, manage_users_headers, other_user):
        other_user.show_phone = True
        other_user.save(update_fields=["show_phone"])
        response = api_client.get("/api/auth/users/search/?q=Other", **manage_users_headers)
        assert response.status_code == 200
        assert self._find(response, other_user.pk)["phone_number"] == other_user.phone_number

    def test_phone_blanked_when_show_phone_false(
        self, api_client, manage_users_headers, other_user
    ):
        other_user.show_phone = False
        other_user.save(update_fields=["show_phone"])
        response = api_client.get("/api/auth/users/search/?q=Other", **manage_users_headers)
        assert response.status_code == 200
        match = self._find(response, other_user.pk)
        # Field stays present (callers depend on the key) but is blanked.
        assert match["phone_number"] == ""

    def test_name_does_not_leak_phone_when_show_phone_false(self, api_client, manage_users_headers):
        # A genuinely nameless member (e.g. pre-onboarding) must not leak the
        # private phone via the name fields — full_name stays empty rather than
        # falling back to the phone number.
        nameless_user = User.objects.create_user(
            phone_number="+12025550999",
            password="namelesspass123",
            first_name="",
            last_name="",
            show_phone=False,
        )
        response = api_client.get("/api/auth/users/search/?q=", **manage_users_headers)
        assert response.status_code == 200
        match = self._find(response, nameless_user.pk)
        assert nameless_user.phone_number not in match["full_name"]
        assert match["full_name"] == ""


@pytest.mark.django_db
class TestUpdateUserRoles:
    def test_manage_users_only_cannot_update_roles(
        self, api_client, manage_users_headers, other_user
    ):
        """MANAGE_USERS alone (a vetter) cannot reassign roles — needs MANAGE_ROLES (Issue 1152)."""
        member_role = Role.objects.get(name="member")
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/roles/",
            {"role_ids": [str(member_role.id)]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)

    def test_non_admin_cannot_grant_admin_role(self, api_client, manage_roles_headers, other_user):
        admin_role = Role.objects.get(name="admin")
        member_role = Role.objects.get(name="member")
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/roles/",
            {"role_ids": [str(member_role.id), str(admin_role.id)]},
            content_type="application/json",
            **manage_roles_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, Code.Role.CANNOT_GRANT_ADMIN)
        assert not other_user.roles.filter(name="admin").exists()

    def test_admin_can_grant_admin_role(self, api_client, other_user):
        admin_role = Role.objects.get(name="admin")
        member_role = Role.objects.get(name="member")
        admin_user = User.objects.create_user(phone_number="+12025550401", password="adminpass123")
        admin_user.roles.add(admin_role)
        refresh = RefreshToken.for_user(admin_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore

        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/roles/",
            {"role_ids": [str(member_role.id), str(admin_role.id)]},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        assert other_user.roles.filter(name="admin").exists()
