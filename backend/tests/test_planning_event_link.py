import uuid
from datetime import timedelta

import pytest
from community.models import (
    AssignmentStatus,
    CoHostInviteStatus,
    EventCoHostInvite,
    EventStatus,
    SlotAssignment,
)
from community.validation import Code
from django.utils import timezone
from notifications.models import Notification, NotificationType
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._events import make_event
from tests._planning import send
from tests._users import make_user

VIEW = PermissionKey.VIEW_EVENT_PLANNING
MANAGE = PermissionKey.MANAGE_EVENT_PLANNING
Status = AssignmentStatus


@pytest.fixture
def slot(year):
    return year.slots.first()


@pytest.fixture
def planner(db):
    return make_user(VIEW)


def assign(slot, user, status=Status.COMMITTED):
    return SlotAssignment.objects.create(slot=slot, user=user, status=status)


def link(api_client, slot_id, event_id, actor):
    url = f"/api/community/planning/slots/{slot_id}/event/"
    return send(api_client, "post", url, {"event_id": str(event_id)}, auth_headers_for(actor))


def invite_for(event, user):
    return EventCoHostInvite.objects.filter(event=event, user=user).first()


@pytest.mark.django_db
class TestLinkEvent:
    def test_committed_planner_links_and_invites_teammates(self, api_client, slot, planner):
        mate = make_user(VIEW)
        proposed = make_user(VIEW)
        assign(slot, planner)
        assign(slot, mate)
        assign(slot, proposed, Status.PROPOSED)
        event = make_event(created_by=planner)

        response = link(api_client, slot.id, event.id, planner)

        assert response.status_code == 200
        assert response.json()["event_id"] == str(event.id)
        slot.refresh_from_db()
        assert slot.event == event
        invite = invite_for(event, mate)
        assert invite.status == CoHostInviteStatus.PENDING
        assert invite.invited_by == planner
        assert invite_for(event, proposed) is None
        assert invite_for(event, planner) is None
        notification = Notification.objects.get()
        assert notification.recipient == mate
        assert notification.notification_type == NotificationType.COHOST_INVITE

    def test_manager_who_hosts_can_link(self, api_client, slot):
        manager = make_user(MANAGE)
        event = make_event(created_by=manager)
        assert link(api_client, slot.id, event.id, manager).status_code == 200

    def test_uncommitted_planner_is_403(self, api_client, slot, planner):
        assign(slot, planner, Status.PROPOSED)
        event = make_event(created_by=planner)
        response = link(api_client, slot.id, event.id, planner)
        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)
        slot.refresh_from_db()
        assert slot.event is None

    def test_committed_on_another_slot_is_403(self, api_client, year, planner):
        first, second = year.slots.all()[:2]
        assign(first, planner)
        event = make_event(created_by=planner)
        assert link(api_client, second.id, event.id, planner).status_code == 403

    def test_caller_must_host_the_event(self, api_client, slot, planner):
        assign(slot, planner)
        event = make_event(created_by=make_user())
        response = link(api_client, slot.id, event.id, planner)
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.NOT_EVENT_HOST)

    def test_slot_with_live_event_is_rejected(self, api_client, slot, planner):
        assign(slot, planner)
        slot.event = make_event(created_by=planner)
        slot.save()
        other = make_event(created_by=planner)
        response = link(api_client, slot.id, other.id, planner)
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.SLOT_HAS_EVENT)

    def test_event_already_linked_to_another_slot_is_rejected(self, api_client, year, planner):
        first, second = year.slots.all()[:2]
        assign(first, planner)
        assign(second, planner)
        event = make_event(created_by=planner)
        assert link(api_client, first.id, event.id, planner).status_code == 200
        response = link(api_client, second.id, event.id, planner)
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.EVENT_ALREADY_LINKED)
        second.refresh_from_db()
        assert second.event is None

    def test_deleted_event_can_be_replaced(self, api_client, slot, planner):
        assign(slot, planner)
        slot.event = make_event(created_by=planner, status=EventStatus.DELETED)
        slot.save()
        event = make_event(created_by=planner)
        assert link(api_client, slot.id, event.id, planner).status_code == 200

    def test_rejected_invites_do_not_undo_the_link(self, api_client, slot, planner):
        mate = make_user(VIEW)
        assign(slot, planner)
        assign(slot, mate)
        past = timezone.now() - timedelta(days=2)
        event = make_event(created_by=planner, start_datetime=past)
        assert link(api_client, slot.id, event.id, planner).status_code == 200
        slot.refresh_from_db()
        assert slot.event == event
        assert invite_for(event, mate) is None

    def test_unknown_slot_and_event(self, api_client, slot, planner):
        assign(slot, planner)
        event = make_event(created_by=planner)
        assert link(api_client, uuid.uuid4(), event.id, planner).status_code == 404
        assert link(api_client, slot.id, uuid.uuid4(), planner).status_code == 404

    def test_unauthenticated(self, api_client, slot):
        url = f"/api/community/planning/slots/{slot.id}/event/"
        body = {"event_id": str(uuid.uuid4())}
        assert send(api_client, "post", url, body).status_code == 401


def set_invite(event, user, status):
    return EventCoHostInvite.objects.create(event=event, user=user, status=status)


def linked_slot(slot, creator):
    slot.event = make_event(created_by=creator)
    slot.save()
    return slot.event


def respond(api_client, assignment, action, actor):
    url = f"/api/community/planning/assignments/{assignment.id}/{action}/"
    return send(api_client, "post", url, headers=auth_headers_for(actor))


@pytest.mark.django_db
class TestInviteGuards:
    def test_link_skips_a_removed_cohost(self, api_client, slot, planner):
        mate = make_user(VIEW)
        other = make_user(VIEW)
        assign(slot, planner)
        assign(slot, mate)
        assign(slot, other)
        event = make_event(created_by=planner)
        set_invite(event, mate, CoHostInviteStatus.REMOVED)

        assert link(api_client, slot.id, event.id, planner).status_code == 200

        assert invite_for(event, mate).status == CoHostInviteStatus.REMOVED
        assert invite_for(event, other).status == CoHostInviteStatus.PENDING
        assert Notification.objects.get().recipient == other

    def test_late_commit_skips_a_removed_cohost(self, api_client, slot, planner):
        event = linked_slot(slot, make_user(VIEW))
        set_invite(event, planner, CoHostInviteStatus.REMOVED)
        respond(api_client, assign(slot, planner, Status.PROPOSED), "commit", planner)
        assert invite_for(event, planner).status == CoHostInviteStatus.REMOVED
        assert not Notification.objects.filter(recipient=planner).exists()

    @pytest.mark.parametrize(
        "old",
        [CoHostInviteStatus.RESCINDED, CoHostInviteStatus.DECLINED, CoHostInviteStatus.EXPIRED],
    )
    def test_late_commit_reinvites_after_other_endings(self, api_client, slot, planner, old):
        event = linked_slot(slot, make_user(VIEW))
        set_invite(event, planner, old)
        respond(api_client, assign(slot, planner, Status.PROPOSED), "commit", planner)
        assert invite_for(event, planner).status == CoHostInviteStatus.PENDING

    def test_creatorless_event_never_notifies_the_planner_of_their_own_invite(
        self, api_client, slot, planner
    ):
        slot.event = make_event()
        slot.save()
        respond(api_client, assign(slot, planner, Status.PROPOSED), "commit", planner)
        assert not Notification.objects.filter(recipient=planner).exists()


@pytest.mark.django_db
class TestRescindOnBackOut:
    def pending_invite(self, slot, planner):
        event = linked_slot(slot, make_user(VIEW))
        set_invite(event, planner, CoHostInviteStatus.PENDING)
        return event

    def test_decline_from_committed_rescinds_pending_invite(self, api_client, slot, planner):
        event = self.pending_invite(slot, planner)
        respond(api_client, assign(slot, planner), "decline", planner)
        assert invite_for(event, planner).status == CoHostInviteStatus.RESCINDED

    @pytest.mark.parametrize("action", ["decline", "withdraw"])
    def test_proposed_planner_keeps_a_manual_invite(self, api_client, slot, planner, action):
        event = self.pending_invite(slot, planner)
        assignment = assign(slot, planner, Status.PROPOSED)
        if action == "decline":
            respond(api_client, assignment, "decline", planner)
        else:
            url = f"/api/community/planning/assignments/{assignment.id}/"
            send(api_client, "delete", url, headers=auth_headers_for(make_user(MANAGE)))
        assert invite_for(event, planner).status == CoHostInviteStatus.PENDING

    def test_withdraw_rescinds_pending_invite(self, api_client, slot, planner):
        event = self.pending_invite(slot, planner)
        assignment = assign(slot, planner)
        url = f"/api/community/planning/assignments/{assignment.id}/"
        coordinator = make_user(MANAGE)
        assert (
            send(api_client, "delete", url, headers=auth_headers_for(coordinator)).status_code
            == 204
        )
        assert invite_for(event, planner).status == CoHostInviteStatus.RESCINDED

    def test_accepted_cohost_is_left_alone(self, api_client, slot, planner):
        event = linked_slot(slot, make_user(VIEW))
        set_invite(event, planner, CoHostInviteStatus.ACCEPTED)
        event.co_hosts.add(planner)
        respond(api_client, assign(slot, planner), "decline", planner)
        assert invite_for(event, planner).status == CoHostInviteStatus.ACCEPTED
        assert event.co_hosts.filter(pk=planner.pk).exists()
