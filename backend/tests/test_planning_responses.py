import uuid

import pytest
from community.models import AssignmentStatus, SlotAssignment
from community.validation import Code
from notifications.models import Notification, NotificationType
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._planning import send
from tests._users import grant, make_attendance_paused, make_user

VIEW = PermissionKey.VIEW_EVENT_PLANNING
MANAGE = PermissionKey.MANAGE_EVENT_PLANNING
Status = AssignmentStatus


@pytest.fixture
def slot(year):
    return year.slots.first()


@pytest.fixture
def planner(db):
    return make_user(VIEW)


def respond(api_client, assignment, action, actor):
    url = f"/api/community/planning/assignments/{assignment.id}/{action}/"
    return send(api_client, "post", url, headers=auth_headers_for(actor))


def assign(slot, user, status=Status.PROPOSED):
    return SlotAssignment.objects.create(slot=slot, user=user, status=status)


@pytest.mark.django_db
class TestRespond:
    def test_commit(self, api_client, slot, planner):
        assignment = assign(slot, planner)
        response = respond(api_client, assignment, "commit", planner)
        assert response.status_code == 200
        assert response.json()["status"] == Status.COMMITTED
        assert response.json()["responded_at"] is not None
        assignment.refresh_from_db()
        assert assignment.status == Status.COMMITTED

    @pytest.mark.parametrize("start", [Status.PROPOSED, Status.COMMITTED])
    def test_decline_from_proposed_or_committed(self, api_client, slot, planner, start):
        assignment = assign(slot, planner, start)
        response = respond(api_client, assignment, "decline", planner)
        assert response.status_code == 200
        assert response.json()["status"] == Status.DECLINED
        assignment.refresh_from_db()
        assert assignment.status == Status.DECLINED

    @pytest.mark.parametrize("action", ["commit", "decline"])
    def test_someone_elses_row_is_404(self, api_client, slot, planner, action):
        assignment = assign(slot, make_user(VIEW))
        response = respond(api_client, assignment, action, planner)
        assert response.status_code == 404
        assert_error_code(response, Code.Planning.ASSIGNMENT_NOT_FOUND)
        assignment.refresh_from_db()
        assert assignment.status == Status.PROPOSED

    @pytest.mark.parametrize("action", ["commit", "decline"])
    def test_unknown_assignment(self, api_client, planner, action):
        response = respond(api_client, SlotAssignment(id=uuid.uuid4()), action, planner)
        assert response.status_code == 404
        assert_error_code(response, Code.Planning.ASSIGNMENT_NOT_FOUND)

    @pytest.mark.parametrize(
        ("action", "start"),
        [
            ("commit", Status.COMMITTED),
            ("commit", Status.DECLINED),
            ("commit", Status.WITHDRAWN),
            ("decline", Status.DECLINED),
            ("decline", Status.WITHDRAWN),
        ],
    )
    def test_not_pending(self, api_client, slot, planner, action, start):
        assignment = assign(slot, planner, start)
        response = respond(api_client, assignment, action, planner)
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.NOT_PENDING)
        assignment.refresh_from_db()
        assert assignment.status == start

    @pytest.mark.parametrize("action", ["commit", "decline"])
    def test_unauthenticated(self, api_client, slot, planner, action):
        url = f"/api/community/planning/assignments/{assign(slot, planner).id}/{action}/"
        assert send(api_client, "post", url).status_code == 401

    def test_rate_limited(self, api_client, slot, planner):
        assignment = assign(slot, planner, Status.DECLINED)
        codes = [respond(api_client, assignment, "commit", planner).status_code for _ in range(11)]
        assert codes[-1] == 429


@pytest.mark.django_db
class TestCoordinatorNotifications:
    @pytest.mark.parametrize(
        ("action", "kind", "verb"),
        [
            ("commit", NotificationType.PLANNING_COMMITTED, "is in for"),
            ("decline", NotificationType.PLANNING_DECLINED, "can't do"),
        ],
    )
    def test_notifies_coordinators_not_actor(self, api_client, slot, action, kind, verb):
        actor = make_user(VIEW, MANAGE, first_name="Pat")
        coordinator = make_user(MANAGE)
        make_user(VIEW)
        paused = make_attendance_paused()
        grant(paused, MANAGE)
        assignment = assign(slot, actor)

        respond(api_client, assignment, action, actor)

        notification = Notification.objects.get()
        assert notification.recipient == coordinator
        assert notification.notification_type == kind
        assert notification.message == f"pat {verb} {slot.label}"
        assert notification.related_user == actor

    def test_failed_response_does_not_notify(self, api_client, slot, planner):
        make_user(MANAGE)
        respond(api_client, assign(slot, planner, Status.DECLINED), "commit", planner)
        assert not Notification.objects.exists()
