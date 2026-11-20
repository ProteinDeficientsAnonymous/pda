import uuid

import pytest
from community.models import AssignmentStatus, SlotAssignment
from community.validation import Code
from django.utils import timezone
from notifications.models import Notification, NotificationType
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._planning import send
from tests._users import grant, make_attendance_paused, make_user

VIEW = PermissionKey.VIEW_EVENT_PLANNING
MANAGE = PermissionKey.MANAGE_EVENT_PLANNING


def propose(api_client, slot, user, actor):
    url = f"/api/community/planning/slots/{slot.id}/assignments/"
    return send(api_client, "post", url, {"user_id": str(user.id)}, auth_headers_for(actor))


def withdraw(api_client, assignment, actor):
    url = f"/api/community/planning/assignments/{assignment.id}/"
    return send(api_client, "delete", url, headers=auth_headers_for(actor))


@pytest.mark.django_db
class TestPropose:
    def test_creates_draft_assignment(self, api_client, slot, coordinator):
        planner = make_user(VIEW)
        response = propose(api_client, slot, planner, coordinator)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == AssignmentStatus.DRAFT
        assert data["user_id"] == str(planner.id)
        assignment = SlotAssignment.objects.get(slot=slot, user=planner)
        assert assignment.proposed_by == coordinator

    def test_manager_without_view_cannot_be_proposed(self, api_client, slot, coordinator):
        assert propose(api_client, slot, make_user(MANAGE), coordinator).status_code == 400

    def test_unauthenticated(self, api_client, slot):
        url = f"/api/community/planning/slots/{slot.id}/assignments/"
        assert send(api_client, "post", url, {"user_id": str(uuid.uuid4())}).status_code == 401

    def test_view_only_forbidden(self, api_client, slot):
        response = propose(api_client, slot, make_user(VIEW), make_user(VIEW))
        assert response.status_code == 403

    def test_unknown_slot(self, api_client, slot, coordinator):
        slot.id = uuid.uuid4()
        response = propose(api_client, slot, make_user(VIEW), coordinator)
        assert response.status_code == 404
        assert_error_code(response, Code.Planning.SLOT_NOT_FOUND)

    def test_rejects_plain_member(self, api_client, slot, coordinator):
        response = propose(api_client, slot, make_user(), coordinator)
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.NOT_A_PLANNER)
        assert not SlotAssignment.objects.exists()

    def test_rejects_paused_planner(self, api_client, slot, coordinator):
        paused = make_attendance_paused()
        grant(paused, VIEW)
        response = propose(api_client, slot, paused, coordinator)
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.NOT_A_PLANNER)

    @pytest.mark.parametrize(
        "status", [AssignmentStatus.DRAFT, AssignmentStatus.PROPOSED, AssignmentStatus.COMMITTED]
    )
    def test_rejects_already_assigned(self, api_client, slot, coordinator, status):
        planner = make_user(VIEW)
        SlotAssignment.objects.create(slot=slot, user=planner, status=status)
        response = propose(api_client, slot, planner, coordinator)
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.ALREADY_ASSIGNED)

    @pytest.mark.parametrize("respond", ["decline", "withdraw"])
    def test_repropose_after_decline_resets_row(self, api_client, slot, coordinator, respond):
        planner = make_user(VIEW)
        old = SlotAssignment.objects.create(
            slot=slot,
            user=planner,
            reminder_count=2,
            last_reminded_at=timezone.now(),
            upcoming_notified_at=timezone.now(),
        )
        getattr(old, respond)()
        old.refresh_from_db()
        assert (
            old.status
            == {"decline": AssignmentStatus.DECLINED, "withdraw": AssignmentStatus.WITHDRAWN}[
                respond
            ]
        )
        assert old.responded_at is not None

        response = propose(api_client, slot, planner, coordinator)

        assert response.status_code == 201
        assert response.json()["id"] == str(old.id)
        assert response.json()["status"] == AssignmentStatus.DRAFT
        old.refresh_from_db()
        assert SlotAssignment.objects.filter(slot=slot, user=planner).count() == 1
        assert old.status == AssignmentStatus.DRAFT
        assert old.responded_at is None
        assert old.reminder_count == 0
        assert old.last_reminded_at is None
        assert old.upcoming_notified_at is None
        assert old.proposed_by == coordinator


@pytest.mark.django_db
class TestWithdraw:
    def test_withdraws_assignment(self, api_client, slot, coordinator):
        assignment = SlotAssignment.objects.create(slot=slot, user=make_user(VIEW))
        assert withdraw(api_client, assignment, coordinator).status_code == 204
        assignment.refresh_from_db()
        assert assignment.status == AssignmentStatus.WITHDRAWN
        assert assignment.responded_at is not None

    def test_view_only_forbidden(self, api_client, slot):
        assignment = SlotAssignment.objects.create(slot=slot, user=make_user(VIEW))
        assert withdraw(api_client, assignment, make_user(VIEW)).status_code == 403

    def test_unknown_assignment(self, api_client, slot, coordinator):
        assignment = SlotAssignment(id=uuid.uuid4())
        response = withdraw(api_client, assignment, coordinator)
        assert response.status_code == 404
        assert_error_code(response, Code.Planning.ASSIGNMENT_NOT_FOUND)

    @pytest.mark.parametrize("status", [AssignmentStatus.DECLINED, AssignmentStatus.WITHDRAWN])
    def test_inactive_assignment_is_untouched(self, api_client, slot, coordinator, status):
        assignment = SlotAssignment.objects.create(slot=slot, user=make_user(VIEW), status=status)
        assert withdraw(api_client, assignment, coordinator).status_code == 204
        assignment.refresh_from_db()
        assert assignment.status == status


@pytest.mark.django_db
class TestNotifications:
    @pytest.mark.parametrize("prior", [None, AssignmentStatus.DECLINED])
    def test_propose_is_silent(self, api_client, slot, coordinator, fake_email_sender, prior):
        planner = make_user(VIEW)
        if prior:
            SlotAssignment.objects.create(slot=slot, user=planner, status=prior)
        assert propose(api_client, slot, planner, coordinator).status_code == 201
        assert not Notification.objects.exists()
        fake_email_sender.send.assert_not_called()

    def test_withdrawing_a_draft_is_silent(self, api_client, slot, coordinator, fake_email_sender):
        assignment = SlotAssignment.objects.create(
            slot=slot, user=make_user(VIEW), status=AssignmentStatus.DRAFT
        )
        assert withdraw(api_client, assignment, coordinator).status_code == 204
        assignment.refresh_from_db()
        assert assignment.status == AssignmentStatus.WITHDRAWN
        assert not Notification.objects.exists()
        fake_email_sender.send.assert_not_called()

    def test_withdraw_notifies_without_email(
        self, api_client, slot, coordinator, fake_email_sender
    ):
        planner = make_user(VIEW)
        assignment = SlotAssignment.objects.create(slot=slot, user=planner)
        withdraw(api_client, assignment, coordinator)
        notification = Notification.objects.get(recipient=planner)
        assert notification.notification_type == NotificationType.PLANNING_WITHDRAWN
        assert notification.message == f"you're no longer down to plan {slot.label}"
        fake_email_sender.send.assert_not_called()

    def test_withdraw_notice_names_the_withdrawing_coordinator(self, api_client, slot, coordinator):
        planner = make_user(VIEW)
        assignment = SlotAssignment.objects.create(
            slot=slot, user=planner, proposed_by=make_user(MANAGE)
        )
        withdraw(api_client, assignment, coordinator)
        assert Notification.objects.get(recipient=planner).related_user == coordinator

    def test_inactive_withdraw_does_not_notify(self, api_client, slot, coordinator):
        planner = make_user(VIEW)
        assignment = SlotAssignment.objects.create(
            slot=slot, user=planner, status=AssignmentStatus.DECLINED
        )
        withdraw(api_client, assignment, coordinator)
        assert not Notification.objects.exists()
