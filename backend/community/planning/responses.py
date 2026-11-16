from collections.abc import Callable
from uuid import UUID

from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import transaction
from ninja import Router

from community.models import AssignmentStatus, SlotAssignment
from community.planning._access import require_view
from community.planning._audit import audit_transition
from community.planning._notify import notify_coordinators
from community.planning._shared import (
    assignment_out,
    get_assignment_or_404,
    invite_planners_to_event,
    rescind_planner_invite,
)
from community.planning.schemas import AssignmentOut
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()

_RESPONSES = {400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut}


def _respond(
    request,
    action: str,
    assignment_id: UUID,
    allowed: tuple[AssignmentStatus, ...],
    apply: Callable[[SlotAssignment], None],
) -> AssignmentOut:
    require_view(request, action)
    with transaction.atomic():
        assignment = get_assignment_or_404(assignment_id, request.auth, lock=True)
        if assignment.status not in allowed:
            raise_validation(Code.Planning.NOT_PENDING, status_code=400)
        before = assignment.status
        was_committed = before == AssignmentStatus.COMMITTED
        apply(assignment)
        audit_transition(request, assignment.status, assignment, before)
    committed = assignment.status == AssignmentStatus.COMMITTED
    notify_coordinators(assignment)
    event = assignment.slot.live_event
    if committed and event is not None:
        invite_planners_to_event(event, [assignment.user_id], event.created_by or request.auth)
    elif was_committed and not committed:
        rescind_planner_invite(assignment.slot, assignment.user_id)
    return assignment_out(assignment)


@router.post(
    "/planning/assignments/{assignment_id}/commit/",
    response={200: AssignmentOut, **_RESPONSES},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def commit_assignment(request, assignment_id: UUID):
    return _respond(
        request,
        "commit_planning_assignment",
        assignment_id,
        (AssignmentStatus.PROPOSED,),
        SlotAssignment.commit,
    )


@router.post(
    "/planning/assignments/{assignment_id}/decline/",
    response={200: AssignmentOut, **_RESPONSES},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def decline_assignment(request, assignment_id: UUID):
    allowed = (AssignmentStatus.PROPOSED, AssignmentStatus.COMMITTED)
    return _respond(
        request, "decline_planning_assignment", assignment_id, allowed, SlotAssignment.decline
    )
