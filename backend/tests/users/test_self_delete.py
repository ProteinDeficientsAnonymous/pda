import pytest
from community._validation import Code
from notifications.models import Notification, NotificationType
from tests._asserts import assert_error_code
from users.models import User
from users.roles import Role

URL = "/api/auth/me/"


@pytest.mark.django_db
class TestSelfDelete:
    def test_requires_auth(self, api_client):
        assert api_client.delete(URL).status_code == 401

    def test_archives_account(self, api_client, auth_headers, test_user):
        response = api_client.delete(URL, **auth_headers)
        assert response.status_code == 204
        test_user.refresh_from_db()
        assert test_user.archived_at is not None

    def test_clears_refresh_cookie(self, api_client, auth_headers):
        response = api_client.delete(URL, **auth_headers)
        assert response.cookies["refresh_token"].value == ""

    def test_token_rejected_after_delete(self, api_client, auth_headers):
        api_client.delete(URL, **auth_headers)
        assert api_client.get(URL, **auth_headers).status_code == 403

    def test_notifies_user_managers_to_remove_from_whatsapp(
        self,
        api_client,
        auth_headers,
        test_user,
        manage_users_user,
        vettor_user,  # noqa: ARG002
    ):
        api_client.delete(URL, **auth_headers)
        notifications = Notification.objects.filter(
            notification_type=NotificationType.ACCOUNT_DELETED
        )
        assert [n.recipient_id for n in notifications] == [manage_users_user.pk]
        n = notifications.get()
        assert n.related_user_id == test_user.pk
        assert "test member" in n.message
        assert "whatsapp" in n.message
        assert "202" in n.message

    def test_last_admin_cannot_delete(self, api_client, auth_headers, test_user):
        admin_role, _ = Role.objects.get_or_create(name="admin", is_default=True)
        test_user.roles.add(admin_role)
        response = api_client.delete(URL, **auth_headers)
        assert response.status_code == 400
        assert_error_code(response, Code.User.CANNOT_DELETE_LAST_ADMIN)
        assert User.objects.get(pk=test_user.pk).archived_at is None
