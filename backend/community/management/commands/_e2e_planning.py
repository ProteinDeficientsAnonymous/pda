from django.db import IntegrityError
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.permissions import PermissionKey

from community.models import PlanningYear

from ._e2e_common import browser_user


def seed_view_planner() -> dict:
    planner = browser_user([PermissionKey.VIEW_EVENT_PLANNING])
    # planning tabs need a year; year is unique, so reuse any and tolerate a parallel seed's insert
    if not PlanningYear.objects.exists():
        try:
            PlanningYear.create_with_default_slots(timezone.now().year)
        except IntegrityError:
            if not PlanningYear.objects.exists():
                raise
    return {"refresh_token": str(RefreshToken.for_user(planner))}
