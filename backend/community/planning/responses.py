from collections.abc import Callable
from uuid import UUID

from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import transaction
from ninja import Router

from community.models import AssignmentStatus, SlotAssignment
from community.planning._notify import notify_coordinators
from community.planning.proposals import assignment_out
from community.planning.schemas import AssignmentOut
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()

_RESPONSES = {400: ErrorOut, 404: ErrorOut, 429: ErrorOut}


def _respond(
    request,
    assignment_id: UUID,
    allowed: tuple[AssignmentStatus, ...],
    apply: Callable[[SlotAssignment], None],
    committed: bool,
) -> AssignmentOut:
    with transaction.atomic():
        assignment = (
            SlotAssignment.objects.select_for_update(of=("self",))
            .select_related("slot", "user")
            .filter(pk=assignment_id, user=request.auth)
            .first()
        )
        if assignment is None:
            raise_validation(Code.Planning.ASSIGNMENT_NOT_FOUND, status_code=404)
        if assignment.status not in allowed:
            raise_validation(Code.Planning.NOT_PENDING, status_code=400)
        apply(assignment)
    notify_coordinators(assignment, committed)
    return assignment_out(assignment)


@router.post(
    "/planning/assignments/{assignment_id}/commit/",
    response={200: AssignmentOut, **_RESPONSES},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def commit_assignment(request, assignment_id: UUID):
    return _respond(
        request, assignment_id, (AssignmentStatus.PROPOSED,), SlotAssignment.commit, True
    )


@router.post(
    "/planning/assignments/{assignment_id}/decline/",
    response={200: AssignmentOut, **_RESPONSES},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def decline_assignment(request, assignment_id: UUID):
    allowed = (AssignmentStatus.PROPOSED, AssignmentStatus.COMMITTED)
    return _respond(request, assignment_id, allowed, SlotAssignment.decline, False)
