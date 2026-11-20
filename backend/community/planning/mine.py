from collections import defaultdict

from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from users.helpers import visible_display_name

from community.models import SlotAssignment, SlotChecklistTick
from community.planning._access import require_view
from community.planning._shared import ACTIVE_STATUSES, slot_out
from community.planning.schemas import MySlotOut, TeammateOut
from community.shared import ErrorOut

router = Router()


@router.get("/planning/me/", response={200: list[MySlotOut], 403: ErrorOut}, auth=gated_jwt)
def list_my_slots(request):
    require_view(request, "list_my_planning_slots")
    mine = list(
        SlotAssignment.objects.filter(user=request.auth, status__in=ACTIVE_STATUSES)
        .select_related("slot__planning_year", "slot__event")
        .order_by("slot__planning_year__year", "slot__order")
    )
    teammates = defaultdict(list)
    others = (
        SlotAssignment.objects.filter(
            slot_id__in=[a.slot_id for a in mine], status__in=ACTIVE_STATUSES
        )
        .exclude(user=request.auth)
        .select_related("user")
        .order_by("proposed_at")
    )
    done = defaultdict(list)
    for tick in SlotChecklistTick.objects.filter(slot_id__in=[a.slot_id for a in mine]):
        done[tick.slot_id].append(str(tick.item_id))
    for other in others:
        teammates[other.slot_id].append(
            TeammateOut(name=visible_display_name(other.user, request.auth), status=other.status)
        )
    return Status(
        200,
        [
            MySlotOut(
                assignment_id=str(a.id),
                status=a.status,
                year=a.slot.planning_year.year,
                slot=slot_out(a.slot),
                teammates=teammates[a.slot_id],
                checklist_done_ids=done[a.slot_id],
            )
            for a in mine
        ],
    )
