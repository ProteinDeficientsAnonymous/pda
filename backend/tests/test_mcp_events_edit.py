from datetime import timedelta
from unittest.mock import patch

import pytest
from audit.models import AuditLogEntry
from community._event_description_templates import OFFICIAL_WALK_TEMPLATE
from community.models import Event, EventStatus, EventType
from django.utils import timezone
from mcp_gateway.confirm import MAX_AGE_SECONDS
from mcp_gateway.event_templates import template_slots

from tests.test_mcp_events_write import _error, _run

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


@pytest.fixture
def make_event(test_user):
    def make(status=EventStatus.ACTIVE, **fields) -> Event:
        start = timezone.now() + timedelta(days=7)
        event = Event.objects.create(
            title="walk", created_by=test_user, start_datetime=start, status=status, **fields
        )
        event.co_hosts.add(test_user)
        return event

    return make


def _publish(user, event, **arguments) -> dict:
    return _run(user, "publish_event", event=str(event.pk), **arguments)


def _publish_refused(user, event, **arguments) -> str:
    return _error(user, "publish_event", event=str(event.pk), **arguments)


def test_publish_refuses_official_draft_with_unfilled_slots(test_user, make_event):
    event = make_event(
        EventStatus.DRAFT, event_type=EventType.OFFICIAL, description=OFFICIAL_WALK_TEMPLATE
    )
    slots = ", ".join(template_slots(OFFICIAL_WALK_TEMPLATE))
    assert (
        _publish_refused(test_user, event)
        == f"fill these template slots in the description first: {slots}"
    )


def test_publish_two_step_publishes_via_mcp(test_user, make_event):
    event = make_event(EventStatus.DRAFT, event_type=EventType.OFFICIAL, description="filled in")
    preview = _publish(test_user, event)
    assert (preview["status"], preview["description"]) == ("draft", "filled in")
    assert Event.objects.get(pk=event.pk).status == EventStatus.DRAFT
    assert _publish(test_user, event, confirm_token=preview["confirm_token"])["status"] == "active"
    assert Event.objects.get(pk=event.pk).status == EventStatus.ACTIVE
    entry = AuditLogEntry.objects.get(action="event_published", target_id=str(event.pk))
    assert entry.details["via"] == "mcp"


def test_publish_token_bound_to_member_event_and_state(test_user, make_event, vettor_user):
    event, other = make_event(EventStatus.DRAFT), make_event(EventStatus.DRAFT)
    event.co_hosts.add(vettor_user)
    token = _publish(test_user, event)["confirm_token"]
    assert "fresh preview" in _publish_refused(vettor_user, event, confirm_token=token)
    assert "fresh preview" in _publish_refused(test_user, other, confirm_token=token)
    later = timezone.now().timestamp() + MAX_AGE_SECONDS + 1
    with patch("django.core.signing.time.time", return_value=later):
        assert "fresh preview" in _publish_refused(test_user, event, confirm_token=token)
    Event.objects.filter(pk=event.pk).update(location="somewhere else")
    assert "fresh preview" in _publish_refused(test_user, event, confirm_token=token)
    assert Event.objects.get(pk=event.pk).status == EventStatus.DRAFT


@pytest.mark.parametrize("change", ["co_hosts", "invited_users", "photo"])
def test_publish_token_bound_to_who_gets_notified(test_user, make_event, vettor_user, change):
    event = make_event(EventStatus.DRAFT)
    token = _publish(test_user, event)["confirm_token"]
    if change == "photo":
        Event.objects.filter(pk=event.pk).update(photo_updated_at=timezone.now())
    else:
        getattr(event, change).add(vettor_user)
    assert "fresh preview" in _publish_refused(test_user, event, confirm_token=token)


def test_publish_token_is_single_use(test_user, make_event):
    event = make_event(EventStatus.DRAFT)
    token = _publish(test_user, event)["confirm_token"]
    _publish(test_user, event, confirm_token=token)
    Event.objects.filter(pk=event.pk).update(status=EventStatus.DRAFT)
    assert "already used" in _publish_refused(test_user, event, confirm_token=token)
    assert Event.objects.get(pk=event.pk).status == EventStatus.DRAFT


def test_publish_refuses_non_draft(test_user, make_event):
    error = _publish_refused(test_user, make_event())
    assert error == "only drafts can be published; this event is active"
