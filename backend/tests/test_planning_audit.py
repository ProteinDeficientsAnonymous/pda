import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.models import AssignmentStatus, SlotAssignment
from django.test import TestCase

from tests._auth import auth_headers_for
from tests._planning import assign, respond, send

Status = AssignmentStatus
BASE = "/api/community/planning"


def call(api_client, method, url, actor, body=None):
    with TestCase.captureOnCommitCallbacks(execute=True):
        return send(api_client, method, url, body, auth_headers_for(actor))


def draft(api_client, slot, user, actor):
    url = f"{BASE}/slots/{slot.id}/assignments/"
    return call(api_client, "post", url, actor, {"user_id": str(user.id)})


def timeline(assignment):
    entries = AuditLogEntry.objects.filter(
        target_type=AuditTargetType.SLOT_ASSIGNMENT, target_id=str(assignment.id)
    ).order_by("created_at")
    return [(e.action, e.details["from"], e.details["to"]) for e in entries]


@pytest.mark.django_db
class TestPlanningAudit:
    def test_full_lifecycle_is_reconstructable(
        self, api_client, slot, planner, coordinator, fake_email_sender
    ):
        draft(api_client, slot, planner, coordinator)
        call(api_client, "post", f"{BASE}/years/2027/proposals/send/", coordinator)
        assignment = SlotAssignment.objects.get(slot=slot, user=planner)
        with TestCase.captureOnCommitCallbacks(execute=True):
            respond(api_client, assignment, "commit", planner)
            respond(api_client, assignment, "decline", planner)
        draft(api_client, slot, planner, coordinator)
        call(api_client, "delete", f"{BASE}/assignments/{assignment.id}/", coordinator)

        assert timeline(assignment) == [
            ("planning_assignment_drafted", None, Status.DRAFT),
            ("planning_assignment_proposed", Status.DRAFT, Status.PROPOSED),
            ("planning_assignment_committed", Status.PROPOSED, Status.COMMITTED),
            ("planning_assignment_declined", Status.COMMITTED, Status.DECLINED),
            ("planning_assignment_drafted", Status.DECLINED, Status.DRAFT),
            ("planning_assignment_withdrawn", Status.DRAFT, Status.WITHDRAWN),
        ]
        entries = AuditLogEntry.objects.filter(target_id=str(assignment.id))
        assert entries.get(action="planning_assignment_committed").actor == planner
        entry = entries.get(action="planning_assignment_withdrawn")
        assert entry.actor == coordinator
        assert entry.details["slot_id"] == str(slot.id)
        assert entry.details["user_id"] == str(planner.id)

    @pytest.mark.parametrize("start", [None, Status.DECLINED])
    def test_confirm_records_prior_status(self, api_client, slot, planner, coordinator, start):
        if start:
            assign(slot, planner, start)
        url = f"{BASE}/slots/{slot.id}/assignments/confirm/"
        call(api_client, "post", url, coordinator, {"user_id": str(planner.id)})
        assignment = SlotAssignment.objects.get(slot=slot, user=planner)
        assert timeline(assignment) == [("planning_assignment_confirmed", start, Status.COMMITTED)]

    def test_withdrawing_inactive_row_logs_nothing(self, api_client, slot, planner, coordinator):
        assignment = assign(slot, planner, Status.DECLINED)
        call(api_client, "delete", f"{BASE}/assignments/{assignment.id}/", coordinator)
        assert timeline(assignment) == []
