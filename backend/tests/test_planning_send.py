from unittest.mock import patch

import pytest
from community.models import AssignmentStatus, PlanningYear
from community.validation import Code
from django.conf import settings
from notifications.email_sender import SendResult
from notifications.models import Notification, NotificationType
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._planning import assign, send
from tests._users import make_user

VIEW = PermissionKey.VIEW_EVENT_PLANNING
MANAGE = PermissionKey.MANAGE_EVENT_PLANNING
DRAFT = AssignmentStatus.DRAFT


@pytest.fixture
def coordinator(db):
    return make_user(MANAGE)


def send_proposals(api_client, actor, year=2027):
    url = f"/api/community/planning/years/{year}/proposals/send/"
    return send(api_client, "post", url, headers=auth_headers_for(actor))


@pytest.mark.django_db
class TestSendProposals:
    def test_sends_one_notice_per_planner(self, api_client, year, coordinator, fake_email_sender):
        planner = make_user(VIEW, email="planner@example.com")
        slots = list(year.slots.order_by("order")[:3])
        rows = [assign(s, planner, DRAFT) for s in reversed(slots)]

        response = send_proposals(api_client, coordinator)

        assert response.status_code == 200
        assert response.json() == {"planners_notified": 1, "proposals_sent": 3}
        for row in rows:
            row.refresh_from_db()
            assert row.status == AssignmentStatus.PROPOSED
            assert row.proposed_by == coordinator
        notification = Notification.objects.get(recipient=planner)
        assert notification.notification_type == NotificationType.PLANNING_PROPOSED
        labels = [s.label for s in slots]
        summary = f"{labels[0]}, {labels[1]} and {labels[2]}"
        assert notification.message == f"you've been asked to plan {summary} — tap to respond"
        assert notification.related_user == coordinator
        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == "planner@example.com"
        assert kwargs["subject"] == f"can you plan {summary}?"
        assert f"{settings.FRONTEND_BASE_URL}/admin/planning" in kwargs["text"]
        fake_email_sender.send.assert_called_once()

    def test_two_planners_get_one_email_each(
        self, api_client, year, coordinator, fake_email_sender
    ):
        a, b = make_user(VIEW), make_user(VIEW)
        s0, s1 = list(year.slots.all()[:2])
        for planner in (a, b):
            assign(s0, planner, DRAFT)
            assign(s1, planner, DRAFT)
        response = send_proposals(api_client, coordinator)
        assert response.json() == {"planners_notified": 2, "proposals_sent": 4}
        assert fake_email_sender.send.call_count == 2
        assert Notification.objects.filter(recipient__in=[a, b]).count() == 2

    def test_skips_other_statuses_and_years(self, api_client, year, coordinator, fake_email_sender):
        s0, s1 = list(year.slots.all()[:2])
        assign(s0, make_user(VIEW))
        assign(s1, make_user(VIEW), AssignmentStatus.DECLINED)
        other = PlanningYear.create_with_default_slots(2028).slots.first()
        assign(other, make_user(VIEW), DRAFT)
        response = send_proposals(api_client, coordinator)
        assert response.json() == {"planners_notified": 0, "proposals_sent": 0}
        assert not Notification.objects.exists()
        fake_email_sender.send.assert_not_called()

    def test_second_send_is_a_noop(self, api_client, slot, coordinator, fake_email_sender):
        assign(slot, make_user(VIEW), DRAFT)
        send_proposals(api_client, coordinator)
        response = send_proposals(api_client, coordinator)
        assert response.json() == {"planners_notified": 0, "proposals_sent": 0}
        assert Notification.objects.count() == 1
        fake_email_sender.send.assert_called_once()

    def test_no_email_address_skips_email(self, api_client, slot, coordinator, fake_email_sender):
        planner = make_user(VIEW, email="")
        assign(slot, planner, DRAFT)
        assert send_proposals(api_client, coordinator).status_code == 200
        assert Notification.objects.filter(recipient=planner).exists()
        fake_email_sender.send.assert_not_called()

    @pytest.mark.parametrize("failure", ["raises", "unsuccessful"])
    def test_email_failure_does_not_fail_request(
        self, api_client, slot, coordinator, fake_email_sender, failure
    ):
        if failure == "raises":
            fake_email_sender.send.side_effect = RuntimeError("boom")
        else:
            fake_email_sender.send.return_value = SendResult(success=False, error="nope")
        planner = make_user(VIEW)
        assign(slot, planner, DRAFT)
        assert send_proposals(api_client, coordinator).status_code == 200
        assert Notification.objects.filter(recipient=planner).exists()

    def test_view_only_forbidden(self, api_client, slot):
        assignment = assign(slot, make_user(VIEW), DRAFT)
        assert send_proposals(api_client, make_user(VIEW)).status_code == 403
        assignment.refresh_from_db()
        assert assignment.status == DRAFT

    def test_unknown_year(self, api_client, year, coordinator):
        response = send_proposals(api_client, coordinator, year=2099)
        assert response.status_code == 404
        assert_error_code(response, Code.Planning.YEAR_NOT_FOUND)


@pytest.mark.django_db
def test_a_failed_notice_unsends_only_that_planners_drafts(api_client, year, coordinator):
    slot = year.slots.order_by("order").first()
    rows = [assign(slot, make_user(VIEW), DRAFT) for _ in range(2)]
    calls = []

    def fail_second(user, slots, by):
        calls.append(user)
        if len(calls) == 2:
            raise RuntimeError("push down")

    api_client.raise_request_exception = True
    with (
        patch("community.planning.proposals.notify_proposed", side_effect=fail_second),
        pytest.raises(RuntimeError),
    ):
        send_proposals(api_client, coordinator)
    for row in rows:
        row.refresh_from_db()
    assert sorted(r.status for r in rows) == sorted([AssignmentStatus.PROPOSED, DRAFT])
