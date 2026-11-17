from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.permissions import PermissionKey

from community.models import PlanningYear

from ._e2e_common import browser_user


def seed_view_planner() -> dict:
    planner = browser_user([PermissionKey.VIEW_EVENT_PLANNING])
    # the planning screen only shows its tabs once a year exists; year is unique, so reuse any
    if not PlanningYear.objects.exists():
        PlanningYear.create_with_default_slots(timezone.now().year)
    return {"refresh_token": str(RefreshToken.for_user(planner))}
