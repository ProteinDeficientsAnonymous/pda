import pytest
from django.utils import timezone
from notifications.models import Notification, NotificationType
from notifications.service import create_account_deleted_notifications
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role


@pytest.mark.django_db
def test_notifies_active_user_managers(test_user, manage_users_user, vettor_user):  # noqa: ARG001
    archived = User.objects.create_user(
        phone_number="+12025550999", first_name="Gone", archived_at=timezone.now()
    )
    archived.roles.add(Role.objects.create(name="old", permissions=[PermissionKey.MANAGE_USERS]))
    create_account_deleted_notifications(test_user)
    n = Notification.objects.get(notification_type=NotificationType.ACCOUNT_DELETED)
    assert n.recipient_id == manage_users_user.pk
    assert n.related_user_id == test_user.pk
    assert "test member" in n.message
    assert "whatsapp" in n.message
    assert "202" in n.message
