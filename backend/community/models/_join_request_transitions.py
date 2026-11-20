from typing import TYPE_CHECKING, NoReturn

from audit.models import AuditTargetType
from django.utils import timezone

from community.field_limits import FieldLimit
from community.models.choices import (
    ALLOWED_JOIN_REQUEST_TRANSITIONS,
    JoinRequestEvent,
    JoinRequestStatus,
    RejectionReason,
)
from community.validation import Code, InvalidStateTransition, TransitionFailure, raise_validation

if TYPE_CHECKING:
    from community.models.join_form import JoinRequest

STATUS_FIELDS = ("status", "status_changed_at", "status_changed_by")

_EVENT_TARGET: dict[JoinRequestEvent, JoinRequestStatus] = {
    JoinRequestEvent.MARK_TENTATIVE: JoinRequestStatus.TENTATIVE,
    JoinRequestEvent.APPROVE: JoinRequestStatus.APPROVED,
    JoinRequestEvent.PROMOTE_ON_CHECK_IN: JoinRequestStatus.APPROVED,
    JoinRequestEvent.REJECT: JoinRequestStatus.REJECTED,
    JoinRequestEvent.UNREJECT: JoinRequestStatus.PENDING,
    JoinRequestEvent.CLOSE: JoinRequestStatus.CLOSED,
}


def normalize_rejection(reason: str, note: str) -> tuple[str, str]:
    """Validate optional rejection reason/note; keep note only for OTHER."""
    if not reason:
        return "", ""
    if reason not in RejectionReason.values:
        raise_validation(
            Code.JoinRequest.INVALID_REJECTION_REASON,
            field="rejection_reason",
            allowed=RejectionReason.values,
        )
    if reason != RejectionReason.OTHER:
        return reason, ""
    cleaned = note.strip()
    if not cleaned:
        raise_validation(Code.JoinRequest.REJECTION_NOTE_REQUIRED, field="rejection_note")
    if len(cleaned) > FieldLimit.REJECTION_NOTE:
        raise_validation(
            Code.JoinRequest.REJECTION_NOTE_TOO_LONG,
            field="rejection_note",
            max_length=FieldLimit.REJECTION_NOTE,
        )
    return reason, cleaned


def _rejection_code(current: JoinRequestStatus, event: JoinRequestEvent) -> str:
    if event == JoinRequestEvent.UNREJECT:
        return Code.JoinRequest.ONLY_REJECTED_CAN_BE_UN_REJECTED
    if current == JoinRequestStatus.TENTATIVE and event == JoinRequestEvent.REJECT:
        return Code.JoinRequest.TENTATIVE_CANNOT_BE_REJECTED
    if current == JoinRequestStatus.PENDING and event in (
        JoinRequestEvent.CLOSE,
        JoinRequestEvent.PROMOTE_ON_CHECK_IN,
    ):
        return Code.JoinRequest.INVALID_STATUS
    return Code.JoinRequest.ALREADY_DECIDED


def reject_join_request_transition(
    join_request: "JoinRequest", event: JoinRequestEvent, code: str
) -> NoReturn:
    to_status = _EVENT_TARGET.get(event)
    raise InvalidStateTransition(
        code,
        TransitionFailure(
            action="join_request_transition_rejected",
            target_type=AuditTargetType.JOIN_REQUEST,
            target_id=str(join_request.id),
            event=str(event),
            from_status=str(join_request.status),
            to_status=str(to_status) if to_status else None,
            extra={"full_name": join_request.full_name},
        ),
    )


def validate_join_request_edge(
    join_request: "JoinRequest", event: JoinRequestEvent
) -> JoinRequestStatus:
    current = JoinRequestStatus(join_request.status)
    target = ALLOWED_JOIN_REQUEST_TRANSITIONS.get((current, event))
    if target is None:
        reject_join_request_transition(join_request, event, _rejection_code(current, event))
    return target


def stamp_join_request_status(
    join_request: "JoinRequest", target: JoinRequestStatus, by
) -> list[str]:
    join_request.status = target
    join_request.status_changed_at = timezone.now()
    join_request.status_changed_by = by
    return list(STATUS_FIELDS)
