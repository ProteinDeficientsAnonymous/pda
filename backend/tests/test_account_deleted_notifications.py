import pytest
from django.utils import timezone
from notifications.models import Notification, NotificationType
from notifications.service import create_account_deleted_notifications
from users.permissions import PermissionKey

from tests._users import make_user


@pytest.mark.django_db
def test_notifies_active_user_managers(test_user, manage_users_user, vettor_user):  # noqa: ARG001
    make_user(PermissionKey.MANAGE_USERS, archived_at=timezone.now())
    create_account_deleted_notifications(test_user)
    n = Notification.objects.get(notification_type=NotificationType.ACCOUNT_DELETED)
    assert n.recipient_id == manage_users_user.pk
    assert n.related_user_id == test_user.pk
    assert "test member" in n.message
    assert "whatsapp" in n.message
    assert "202" in n.message
