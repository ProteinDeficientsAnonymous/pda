from django.db.models import Q, QuerySet
from users.models import User
from users.permissions import PermissionKey


def planner_users() -> QuerySet[User]:
    viewers = User.objects.with_permission(PermissionKey.VIEW_EVENT_PLANNING).values("pk")
    managers = User.objects.with_permission(PermissionKey.MANAGE_EVENT_PLANNING).values("pk")
    return User.objects.active_members().filter(Q(pk__in=viewers) | Q(pk__in=managers))
