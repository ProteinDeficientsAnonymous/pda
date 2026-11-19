import logging

from config.audit import AuditTarget, AuditTargetType, audit_log

from community.models import SlotAssignment


def audit_transition(request, action: str, assignment: SlotAssignment, before: str | None) -> None:
    details = {
        "slot_id": str(assignment.slot_id),
        "user_id": str(assignment.user_id),
        "from": before,
        "to": assignment.status,
    }
    target = AuditTarget(AuditTargetType.SLOT_ASSIGNMENT, str(assignment.pk), details)
    audit_log(logging.INFO, f"planning_assignment_{action}", request, target)
