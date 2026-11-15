from django.db.models import Q, QuerySet
from users.models import User
from users.permissions import PermissionKey


def _holders(permission: PermissionKey) -> QuerySet[User]:
    return User.objects.with_permission(permission).values("pk")


def planner_users() -> QuerySet[User]:
    viewers = _holders(PermissionKey.VIEW_EVENT_PLANNING)
    managers = _holders(PermissionKey.MANAGE_EVENT_PLANNING)
    return User.objects.active_members().filter(Q(pk__in=viewers) | Q(pk__in=managers))


def coordinator_users() -> QuerySet[User]:
    return User.objects.active_members().filter(
        pk__in=_holders(PermissionKey.MANAGE_EVENT_PLANNING)
    )
