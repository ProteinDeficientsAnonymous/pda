from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import transaction
from ninja import Router
from ninja.responses import Status

from community.models import PlanningAvailability
from community.planning._access import require_view
from community.planning.schemas import AvailabilityIn, AvailabilityOut
from community.planning.years import get_year_or_404
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()


def _availability_out(row: PlanningAvailability | None) -> AvailabilityOut:
    if row is None:
        return AvailabilityOut(
            submitted=False,
            biannual_interest=None,
            monthly_count=0,
            slot_ids=[],
            updated_at=None,
        )
    return AvailabilityOut(
        submitted=True,
        biannual_interest=row.biannual_interest,
        monthly_count=row.monthly_count,
        slot_ids=[str(pk) for pk in row.available_slots.values_list("pk", flat=True)],
        updated_at=row.updated_at,
    )


@router.get(
    "/planning/years/{year}/availability/me/",
    response={200: AvailabilityOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_my_availability(request, year: int):
    require_view(request, "get_my_planning_availability")
    planning_year = get_year_or_404(year)
    row = PlanningAvailability.objects.filter(
        planning_year=planning_year, user=request.auth
    ).first()
    return Status(200, _availability_out(row))


@router.put(
    "/planning/years/{year}/availability/me/",
    response={200: AvailabilityOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def put_my_availability(request, year: int, payload: AvailabilityIn):
    require_view(request, "put_my_planning_availability")
    planning_year = get_year_or_404(year)
    slots = list(planning_year.slots.filter(pk__in=payload.slot_ids))
    if len(slots) != len(set(payload.slot_ids)):
        raise_validation(Code.Planning.SLOT_NOT_IN_YEAR, field="slot_ids", status_code=400)
    with transaction.atomic():
        row, _ = PlanningAvailability.objects.update_or_create(
            planning_year=planning_year,
            user=request.auth,
            defaults={
                "biannual_interest": payload.biannual_interest,
                "monthly_count": payload.monthly_count,
            },
        )
        row.available_slots.set(slots)
    return Status(200, _availability_out(row))
