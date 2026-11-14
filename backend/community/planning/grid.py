from config.auth import gated_jwt
from django.db.models import Prefetch, Q
from ninja import Router
from ninja.responses import Status
from users.helpers import visible_display_name
from users.models import User

from community.models import AssignmentStatus, PlanningAvailability, PlanningSlot, SlotAssignment
from community.planning._access import require_manage
from community.planning._planners import planner_users
from community.planning.proposals import assignment_out
from community.planning.schemas import GridOut, PlannerColumnOut
from community.planning.years import get_year_or_404, slot_out
from community.shared import ErrorOut

router = Router()


def _column(
    user: User, viewer: User, row: PlanningAvailability | None, is_planner: bool
) -> PlannerColumnOut:
    return PlannerColumnOut(
        user_id=str(user.id),
        name=visible_display_name(user, viewer),
        is_planner=is_planner,
        has_email=bool(user.email),
        submitted=row is not None,
        biannual_interest=row.biannual_interest if row else None,
        monthly_count=row.monthly_count if row else 0,
        available_slot_ids=[str(s.pk) for s in row.available_slots.all()] if row else [],
    )


@router.get(
    "/planning/years/{year}/grid/",
    response={200: GridOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_grid(request, year: int):
    require_manage(request, "get_planning_grid")
    planning_year = get_year_or_404(year)
    slots = list(planning_year.slots.select_related("event"))
    assignments = list(
        SlotAssignment.objects.filter(slot__planning_year=planning_year).exclude(
            status=AssignmentStatus.WITHDRAWN
        )
    )
    rows = {
        row.user_id: row
        for row in PlanningAvailability.objects.filter(
            planning_year=planning_year
        ).prefetch_related(Prefetch("available_slots", queryset=PlanningSlot.objects.only("pk")))
    }
    planner_ids = set(planner_users().values_list("pk", flat=True))
    in_grid = Q(pk__in=planner_ids) | Q(pk__in=rows.keys())
    in_grid |= Q(pk__in=[a.user_id for a in assignments])
    columns = [
        _column(u, request.auth, rows.get(u.id), u.id in planner_ids)
        for u in User.objects.filter(in_grid)
    ]
    columns.sort(key=lambda c: c.name.casefold())
    return Status(
        200,
        GridOut(
            slots=[slot_out(s) for s in slots],
            planners=columns,
            assignments=[assignment_out(a) for a in assignments],
        ),
    )
