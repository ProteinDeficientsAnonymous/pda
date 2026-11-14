from uuid import UUID

from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status

from community.models import AssignmentStatus, SlotAssignment
from community.planning._access import require_manage
from community.planning._planners import planner_users
from community.planning.schemas import AssignmentOut, ProposeIn
from community.planning.years import get_slot_or_404
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()

_ACTIVE = (AssignmentStatus.PROPOSED, AssignmentStatus.COMMITTED)


def _assignment_out(assignment: SlotAssignment) -> AssignmentOut:
    return AssignmentOut(
        id=str(assignment.id),
        slot_id=str(assignment.slot_id),
        user_id=str(assignment.user_id),
        status=assignment.status,
        proposed_at=assignment.proposed_at,
        responded_at=assignment.responded_at,
    )


@router.post(
    "/planning/slots/{slot_id}/assignments/",
    response={201: AssignmentOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def propose_assignment(request, slot_id: UUID, payload: ProposeIn):
    require_manage(request, "propose_planning_assignment")
    slot = get_slot_or_404(slot_id)
    user = planner_users().filter(pk=payload.user_id).first()
    if user is None:
        raise_validation(Code.Planning.NOT_A_PLANNER, field="user_id", status_code=400)
    assignment, created = SlotAssignment.objects.get_or_create(
        slot=slot, user=user, defaults={"proposed_by": request.auth}
    )
    if not created:
        if assignment.status in _ACTIVE:
            raise_validation(Code.Planning.ALREADY_ASSIGNED, field="user_id", status_code=400)
        assignment.propose(request.auth)
    return Status(201, _assignment_out(assignment))


@router.delete(
    "/planning/assignments/{assignment_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def withdraw_assignment(request, assignment_id: UUID):
    require_manage(request, "withdraw_planning_assignment")
    try:
        assignment = SlotAssignment.objects.select_related("slot", "user").get(pk=assignment_id)
    except SlotAssignment.DoesNotExist:
        raise_validation(Code.Planning.ASSIGNMENT_NOT_FOUND, status_code=404)
    if assignment.status in _ACTIVE:
        assignment.withdraw()
    return Status(204, None)
