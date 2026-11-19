import pytest
from community.models import AssignmentStatus, CoHostInviteStatus, EventCoHostInvite, SlotAssignment
from community.validation import Code
from django.test import TestCase
from django.utils import timezone
from notifications.models import Notification, NotificationType
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._events import make_event
from tests._planning import assign, send
from tests._users import make_user

VIEW = PermissionKey.VIEW_EVENT_PLANNING
MANAGE = PermissionKey.MANAGE_EVENT_PLANNING


def confirm(api_client, slot, user, actor):
    url = f"/api/community/planning/slots/{slot.id}/assignments/confirm/"
    with TestCase.captureOnCommitCallbacks(execute=True):
        return send(api_client, "post", url, {"user_id": str(user.id)}, auth_headers_for(actor))


@pytest.mark.django_db
class TestConfirm:
    def test_creates_committed_assignment(self, api_client, slot, planner, coordinator):
        response = confirm(api_client, slot, planner, coordinator)
        assert response.status_code == 201
        assert response.json()["status"] == AssignmentStatus.COMMITTED
        assignment = SlotAssignment.objects.get(slot=slot, user=planner)
        assert assignment.proposed_by == coordinator
        assert assignment.responded_at == assignment.proposed_at

    @pytest.mark.parametrize(
        "status", [AssignmentStatus.DRAFT, AssignmentStatus.PROPOSED, AssignmentStatus.DECLINED]
    )
    def test_commits_existing_row(self, api_client, slot, planner, coordinator, status):
        old = SlotAssignment.objects.create(
            slot=slot,
            user=planner,
            status=status,
            reminder_count=2,
            last_reminded_at=timezone.now(),
        )
        response = confirm(api_client, slot, planner, coordinator)
        assert response.json()["id"] == str(old.id)
        old.refresh_from_db()
        assert old.status == AssignmentStatus.COMMITTED
        assert old.reminder_count == 0
        assert old.last_reminded_at is None

    def test_rejects_already_committed(self, api_client, slot, planner, coordinator):
        assign(slot, planner, AssignmentStatus.COMMITTED)
        response = confirm(api_client, slot, planner, coordinator)
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.ALREADY_ASSIGNED)

    def test_rejects_non_planner(self, api_client, slot, coordinator):
        response = confirm(api_client, slot, make_user(MANAGE), coordinator)
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.NOT_A_PLANNER)
        assert not SlotAssignment.objects.exists()

    def test_planner_without_manage_forbidden(self, api_client, slot, planner):
        assert confirm(api_client, slot, planner, planner).status_code == 403
        assert not SlotAssignment.objects.exists()


@pytest.mark.django_db
class TestConfirmNotifications:
    def test_notifies_and_emails_the_planner(
        self, api_client, slot, planner, coordinator, fake_email_sender
    ):
        confirm(api_client, slot, planner, coordinator)
        notification = Notification.objects.get(recipient=planner)
        assert notification.notification_type == NotificationType.PLANNING_COMMITTED
        assert notification.related_user == coordinator
        assert f"put you down to plan {slot.label}" in notification.message
        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == planner.email
        assert kwargs["subject"] == f"you're planning {slot.label} 🌱"

    def test_confirming_yourself_is_silent(self, api_client, slot, fake_email_sender):
        me = make_user(VIEW, MANAGE)
        assert confirm(api_client, slot, me, me).status_code == 201
        assert not Notification.objects.exists()
        fake_email_sender.send.assert_not_called()

    def test_linked_event_invites_planner_as_cohost(self, api_client, slot, planner, coordinator):
        creator = make_user(VIEW)
        slot.event = make_event(created_by=creator)
        slot.save()
        confirm(api_client, slot, planner, coordinator)
        invite = EventCoHostInvite.objects.get(event=slot.event, user=planner)
        assert invite.status == CoHostInviteStatus.PENDING
        assert invite.invited_by == creator

    def test_no_event_no_invite(self, api_client, slot, planner, coordinator):
        confirm(api_client, slot, planner, coordinator)
        assert not EventCoHostInvite.objects.exists()
