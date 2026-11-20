from uuid import UUID

from config.auth import gated_jwt
from django.db import transaction
from django.db.models import Max
from ninja import Router
from ninja.responses import Status

from community.models import (
    AssignmentStatus,
    PlanningChecklistItem,
    SlotAssignment,
    SlotChecklistTick,
)
from community.planning._access import require_manage, require_manage_or, require_view
from community.planning._shared import get_slot_or_404
from community.planning.schemas import (
    ChecklistItemIn,
    ChecklistItemOut,
    ChecklistItemPatchIn,
    ChecklistOrderIn,
    ChecklistTickIn,
    SlotChecklistOut,
)
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()


def _item_out(item: PlanningChecklistItem) -> ChecklistItemOut:
    return ChecklistItemOut(id=str(item.id), text=item.text, detail=item.detail)


def _get_item_or_404(item_id: UUID) -> PlanningChecklistItem:
    try:
        return PlanningChecklistItem.objects.get(pk=item_id)
    except PlanningChecklistItem.DoesNotExist:
        raise_validation(Code.Planning.CHECKLIST_ITEM_NOT_FOUND, status_code=404)


def _all_items() -> list[ChecklistItemOut]:
    return [_item_out(i) for i in PlanningChecklistItem.objects.all()]


@router.get(
    "/planning/checklist/", response={200: list[ChecklistItemOut], 403: ErrorOut}, auth=gated_jwt
)
def list_checklist(request):
    require_view(request, "list_planning_checklist")
    return Status(200, _all_items())


@router.post(
    "/planning/checklist/", response={201: ChecklistItemOut, 403: ErrorOut}, auth=gated_jwt
)
def create_checklist_item(request, payload: ChecklistItemIn):
    require_manage(request, "create_planning_checklist_item")
    with transaction.atomic():
        last = PlanningChecklistItem.objects.aggregate(last=Max("order"))["last"] or 0
        item = PlanningChecklistItem.objects.create(order=last + 1, **payload.model_dump())
    return Status(201, _item_out(item))


@router.put(
    "/planning/checklist/order/",
    response={200: list[ChecklistItemOut], 403: ErrorOut},
    auth=gated_jwt,
)
def reorder_checklist(request, payload: ChecklistOrderIn):
    require_manage(request, "reorder_planning_checklist")
    order = {item_id: i for i, item_id in enumerate(payload.ids, 1)}
    PlanningChecklistItem.objects.bulk_update(
        [PlanningChecklistItem(id=item_id, order=i) for item_id, i in order.items()], ["order"]
    )
    return Status(200, _all_items())


@router.patch(
    "/planning/checklist/{item_id}/",
    response={200: ChecklistItemOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def update_checklist_item(request, item_id: UUID, payload: ChecklistItemPatchIn):
    require_manage(request, "update_planning_checklist_item")
    item = _get_item_or_404(item_id)
    changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    for field, value in changes.items():
        setattr(item, field, value)
    item.save(update_fields=list(changes) or None)
    return Status(200, _item_out(item))


@router.delete(
    "/planning/checklist/{item_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def delete_checklist_item(request, item_id: UUID):
    require_manage(request, "delete_planning_checklist_item")
    _get_item_or_404(item_id).delete()
    return Status(204, None)


@router.put(
    "/planning/slots/{slot_id}/checklist/{item_id}/",
    response={200: SlotChecklistOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def tick_checklist_item(request, slot_id: UUID, item_id: UUID, payload: ChecklistTickIn):
    require_view(request, "tick_planning_checklist_item")
    slot = get_slot_or_404(slot_id)
    committed = SlotAssignment.objects.filter(
        slot=slot, user=request.auth, status=AssignmentStatus.COMMITTED
    ).exists()
    require_manage_or(request, "tick_planning_checklist_item", committed)
    item = _get_item_or_404(item_id)
    if payload.done:
        SlotChecklistTick.objects.get_or_create(
            slot=slot, item=item, defaults={"done_by": request.auth}
        )
    else:
        SlotChecklistTick.objects.filter(slot=slot, item=item).delete()
    done_ids = slot.checklist_ticks.values_list("item_id", flat=True)
    return Status(200, SlotChecklistOut(done_ids=[str(i) for i in done_ids]))
