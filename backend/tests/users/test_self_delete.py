import pytest
from community._validation import Code
from notifications.models import Notification, NotificationType
from tests._asserts import assert_error_code
from users.models import User
from users.roles import Role

URL = "/api/auth/me/delete/"
PASSWORD = {"password": "testpass123"}


def _delete(api_client, headers, body=PASSWORD):
    return api_client.post(URL, body, content_type="application/json", **headers)


@pytest.mark.django_db
class TestSelfDelete:
    def test_archives_and_logs_out(self, api_client, auth_headers, test_user):
        response = _delete(api_client, auth_headers)
        assert response.status_code == 204
        assert response.cookies["refresh_token"].value == ""
        test_user.refresh_from_db()
        assert test_user.archived_at is not None
        assert api_client.get("/api/auth/me/", **auth_headers).status_code == 403

    def test_wrong_password_rejected(self, api_client, auth_headers, test_user):
        response = _delete(api_client, auth_headers, {"password": "nope"})
        assert response.status_code == 400
        assert_error_code(response, Code.Auth.CURRENT_PASSWORD_INCORRECT)
        test_user.refresh_from_db()
        assert test_user.archived_at is None

    def test_onboarding_session_cannot_delete(self, api_client, auth_headers, test_user):
        test_user.needs_onboarding = True
        test_user.save(update_fields=["needs_onboarding"])
        assert _delete(api_client, auth_headers).status_code == 403

    def test_notifies_user_managers(self, api_client, auth_headers, test_user, manage_users_user):
        _delete(api_client, auth_headers)
        assert Notification.objects.filter(
            recipient=manage_users_user,
            related_user=test_user,
            notification_type=NotificationType.ACCOUNT_DELETED,
        ).exists()

    def test_last_admin_cannot_delete(self, api_client, auth_headers, test_user):
        admin_role, _ = Role.objects.get_or_create(name="admin", is_default=True)
        test_user.roles.add(admin_role)
        response = _delete(api_client, auth_headers)
        assert response.status_code == 400
        assert_error_code(response, Code.User.CANNOT_DELETE_LAST_ADMIN)
        assert User.objects.get(pk=test_user.pk).archived_at is None
