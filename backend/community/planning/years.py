from config.auth import gated_jwt
from django.db import IntegrityError
from ninja import Router
from ninja.responses import Status

from community.models import PlanningYear
from community.planning._access import require_manage, require_view
from community.planning.schemas import PlanningYearIn, PlanningYearOut
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()


def get_year_or_404(year: int) -> PlanningYear:
    try:
        return PlanningYear.objects.get(year=year)
    except PlanningYear.DoesNotExist:
        raise_validation(Code.Planning.YEAR_NOT_FOUND, status_code=404)


def _year_out(planning_year: PlanningYear) -> PlanningYearOut:
    return PlanningYearOut(id=str(planning_year.id), year=planning_year.year)


@router.get(
    "/planning/years/",
    response={200: list[PlanningYearOut], 403: ErrorOut},
    auth=gated_jwt,
)
def list_years(request):
    require_view(request, "list_planning_years")
    return Status(200, [_year_out(y) for y in PlanningYear.objects.all()])


@router.post(
    "/planning/years/",
    response={201: PlanningYearOut, 400: ErrorOut, 403: ErrorOut},
    auth=gated_jwt,
)
def create_year(request, payload: PlanningYearIn):
    require_manage(request, "create_planning_year")
    try:
        planning_year = PlanningYear.create_with_default_slots(payload.year)
    except IntegrityError:
        raise_validation(Code.Planning.YEAR_EXISTS, field="year", status_code=400)
    return Status(201, _year_out(planning_year))
