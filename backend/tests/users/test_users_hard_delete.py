import logging

import pytest
from community._validation import Code
from django.utils import timezone
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
class TestListHasLoggedIn:
    def _find(self, response, user):
        return next(u for u in response.json() if u["id"] == str(user.pk))

    def test_never_logged_in_reports_false(self, api_client, manage_users_headers, other_user):
        assert other_user.last_login is None
        response = api_client.get("/api/auth/users/", **manage_users_headers)
        assert response.status_code == 200
        assert self._find(response, other_user)["has_logged_in"] is False

    def test_logged_in_reports_true(self, api_client, manage_users_headers, other_user):
        other_user.last_login = timezone.now()
        other_user.save(update_fields=["last_login"])
        response = api_client.get("/api/auth/users/", **manage_users_headers)
        assert response.status_code == 200
        assert self._find(response, other_user)["has_logged_in"] is True


@pytest.mark.django_db
class TestHardDeleteUser:
    def _url(self, user):
        return f"/api/auth/users/{user.pk}/hard/"

    def test_hard_delete_not_found(self, api_client, manage_users_headers):
        response = api_client.delete(
            "/api/auth/users/00000000-0000-0000-0000-000000000000/hard/",
            **manage_users_headers,
        )
        assert response.status_code == 404
        assert_error_code(response, Code.User.NOT_FOUND)

    def test_hard_delete_requires_auth(self, api_client, other_user):
        response = api_client.delete(self._url(other_user))
        assert response.status_code == 401

    def test_hard_delete_requires_permission(self, api_client, auth_headers, other_user):
        response = api_client.delete(self._url(other_user), **auth_headers)
        assert response.status_code == 403

    def test_hard_delete_never_logged_in_removes_row_and_cascades(
        self, api_client, manage_users_headers, other_user
    ):
        assert other_user.last_login is None
        token = MagicLoginToken.create_for_user(other_user)
        response = api_client.delete(self._url(other_user), **manage_users_headers)
        assert response.status_code == 204
        assert not User.objects.filter(pk=other_user.pk).exists()
        assert not MagicLoginToken.objects.filter(pk=token.pk).exists()

    def test_hard_delete_logged_in_user_returns_400(
        self, api_client, manage_users_headers, other_user
    ):
        other_user.last_login = timezone.now()
        other_user.save(update_fields=["last_login"])

        response = api_client.delete(self._url(other_user), **manage_users_headers)
        assert response.status_code == 400
        assert_error_code(response, Code.User.CANNOT_HARD_DELETE_LOGGED_IN)
        assert User.objects.filter(pk=other_user.pk).exists()

    def test_hard_delete_self_returns_400(
        self, api_client, manage_users_headers, manage_users_user
    ):
        response = api_client.delete(self._url(manage_users_user), **manage_users_headers)
        assert response.status_code == 400
        assert_error_code(response, Code.User.CANNOT_DELETE_SELF)

    def test_hard_delete_last_admin_returns_400(self, api_client, manage_users_headers, other_user):
        admin_role = Role.objects.get(name="admin", is_default=True)
        other_user.roles.add(admin_role)

        response = api_client.delete(self._url(other_user), **manage_users_headers)
        assert response.status_code == 400
        assert_error_code(response, Code.User.CANNOT_DELETE_LAST_ADMIN)

    def test_hard_delete_emits_audit_log(
        self, api_client, manage_users_headers, other_user, caplog
    ):
        _capture_audit(caplog)
        with caplog.at_level(logging.WARNING, logger="pda.audit"):
            response = api_client.delete(self._url(other_user), **manage_users_headers)
        assert response.status_code == 204
        assert any("user_hard_deleted" in r.getMessage() for r in caplog.records)
