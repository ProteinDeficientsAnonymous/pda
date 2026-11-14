from uuid import UUID

from config.auth import gated_jwt
from django.db import IntegrityError, transaction
from django.db.models import Max
from ninja import Router
from ninja.responses import Status

from community.models import PlanningSlot, PlanningYear
from community.planning._access import require_manage, require_view
from community.planning.schemas import (
    PlanningSlotIn,
    PlanningSlotOut,
    PlanningSlotPatchIn,
    PlanningYearIn,
    PlanningYearOut,
)
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()


def get_year_or_404(year: int) -> PlanningYear:
    try:
        return PlanningYear.objects.get(year=year)
    except PlanningYear.DoesNotExist:
        raise_validation(Code.Planning.YEAR_NOT_FOUND, status_code=404)


def get_slot_or_404(slot_id: UUID) -> PlanningSlot:
    try:
        return PlanningSlot.objects.select_related("event").get(pk=slot_id)
    except PlanningSlot.DoesNotExist:
        raise_validation(Code.Planning.SLOT_NOT_FOUND, status_code=404)


def _year_out(planning_year: PlanningYear) -> PlanningYearOut:
    return PlanningYearOut(id=str(planning_year.id), year=planning_year.year)


def slot_out(slot: PlanningSlot) -> PlanningSlotOut:
    event = slot.live_event
    return PlanningSlotOut(
        id=str(slot.id),
        label=slot.label,
        month=slot.month,
        kind=slot.kind,
        order=slot.order,
        event_id=str(event.id) if event else None,
        event_slug=event.slug if event else None,
        event_status=event.status if event else None,
    )


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


@router.get(
    "/planning/years/{year}/slots/",
    response={200: list[PlanningSlotOut], 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def list_slots(request, year: int):
    require_view(request, "list_planning_slots")
    slots = get_year_or_404(year).slots.select_related("event")
    return Status(200, [slot_out(s) for s in slots])


@router.post(
    "/planning/years/{year}/slots/",
    response={201: PlanningSlotOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def create_slot(request, year: int, payload: PlanningSlotIn):
    require_manage(request, "create_planning_slot")
    planning_year = get_year_or_404(year)
    with transaction.atomic():
        last = planning_year.slots.aggregate(last=Max("order"))["last"] or 0
        slot = PlanningSlot.objects.create(
            planning_year=planning_year, order=last + 1, **payload.model_dump()
        )
    return Status(201, slot_out(slot))


@router.patch(
    "/planning/slots/{slot_id}/",
    response={200: PlanningSlotOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def update_slot(request, slot_id: UUID, payload: PlanningSlotPatchIn):
    require_manage(request, "update_planning_slot")
    slot = get_slot_or_404(slot_id)
    changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    for field, value in changes.items():
        setattr(slot, field, value)
    slot.save(update_fields=list(changes) or None)
    return Status(200, slot_out(slot))


@router.delete(
    "/planning/slots/{slot_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def delete_slot(request, slot_id: UUID):
    require_manage(request, "delete_planning_slot")
    get_slot_or_404(slot_id).delete()
    return Status(204, None)
