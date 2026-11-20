from django.db.models import QuerySet
from users.models import Role, User
from users.permissions import PermissionKey


def _holders(permission: PermissionKey) -> QuerySet[User]:
    return User.objects.with_permission(permission).values("pk")


def _granted_holders(permission: PermissionKey) -> QuerySet[User]:
    # Stored grants only, so the admin role's all-permissions default doesn't make every admin a planner.
    role_ids = [
        r.id
        for r in Role.objects.all()
        if isinstance(r.permissions, list) and permission in r.permissions
    ]
    return User.objects.members().filter(roles__id__in=role_ids).values("pk")


def planner_users() -> QuerySet[User]:
    return User.objects.active_members().filter(
        pk__in=_granted_holders(PermissionKey.VIEW_EVENT_PLANNING)
    )


def coordinator_users() -> QuerySet[User]:
    return User.objects.active_members().filter(
        pk__in=_holders(PermissionKey.MANAGE_EVENT_PLANNING)
    )
