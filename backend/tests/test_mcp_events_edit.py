import asyncio
import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from audit.models import AuditLogEntry
from community._event_description_templates import OFFICIAL_WALK_TEMPLATE
from community.models import Event, EventRSVP, EventStatus, EventTag, EventType, RSVPStatus
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp_gateway.confirm import MAX_AGE_SECONDS
from mcp_gateway.event_templates import template_slots
from mcp_gateway.server import pda_mcp

from tests._public_rsvp_helpers import make_non_member
from tests.test_mcp_events_write import _error, _run
from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)
PRICE = {"price": "$20"}


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


def _update(user, event, changes=PRICE, **arguments) -> dict:
    return _run(user, "update_event", event=str(event.pk), changes=changes, **arguments)


def _update_refused(user, event, changes=PRICE, **arguments) -> str:
    return _error(user, "update_event", event=str(event.pk), changes=changes, **arguments)


def test_draft_edit_applies_directly(test_user, make_event):
    event = make_event(EventStatus.DRAFT)
    assert _update(test_user, event)["price"] == "$20"
    assert Event.objects.get(pk=event.pk).price == "$20"


def test_live_edit_previews_then_applies_with_token(test_user, make_event):
    event = make_event(price="$15")
    preview = _update(test_user, event)
    assert preview["changes"] == {"price": {"before": "$15", "after": "$20"}}
    assert Event.objects.get(pk=event.pk).price == "$15"
    assert "fresh preview" in _update_refused(
        test_user, event, {"price": "$25"}, confirm_token=preview["confirm_token"]
    )
    _update(test_user, event, confirm_token=preview["confirm_token"])
    assert Event.objects.get(pk=event.pk).price == "$20"
    entry = AuditLogEntry.objects.get(action="event_updated", target_id=str(event.pk))
    assert entry.details["via"] == "mcp"


def test_non_host_refused_by_view(make_event, vettor_user):
    event = make_event()
    token = _update(vettor_user, event)["confirm_token"]
    assert json.loads(_update_refused(vettor_user, event, confirm_token=token))["status"] == 403


def test_removing_non_member_rsvps_needs_confirmed_force(test_user, make_event):
    event = make_event(event_type=EventType.OFFICIAL, rsvp_enabled=True)
    guest = make_non_member("+12025550177", "n@e.com")
    EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.ATTENDING)
    off, force = {"rsvp_enabled": False}, {"remove_non_member_rsvps": True}
    token = _update(test_user, event, off)["confirm_token"]
    error = _update_refused(test_user, event, off, confirm_token=token)
    assert error.startswith("nothing was saved") and "remove_non_member_rsvps" in error
    assert "fresh preview" in _update_refused(test_user, event, off, confirm_token=token, **force)
    token = _update(test_user, event, off, **force)["confirm_token"]
    _update(test_user, event, off, confirm_token=token, **force)
    assert not Event.objects.get(pk=event.pk).rsvp_enabled


def test_live_edit_token_is_single_use(test_user, make_event):
    event = make_event(price="$15")
    token = _update(test_user, event)["confirm_token"]
    _update(test_user, event, confirm_token=token)
    Event.objects.filter(pk=event.pk).update(price="$15")
    assert "already used" in _update_refused(test_user, event, confirm_token=token)
    assert Event.objects.get(pk=event.pk).price == "$15"


def test_publish_and_update_tokens_are_not_interchangeable(test_user, make_event):
    event = make_event()
    update_token = _update(test_user, event)["confirm_token"]
    Event.objects.filter(pk=event.pk).update(status=EventStatus.DRAFT)
    assert "fresh preview" in _publish_refused(test_user, event, confirm_token=update_token)
    publish_token = _publish(test_user, event)["confirm_token"]
    Event.objects.filter(pk=event.pk).update(status=EventStatus.ACTIVE)
    assert "fresh preview" in _update_refused(test_user, event, confirm_token=publish_token)
    assert Event.objects.get(pk=event.pk).price == ""


@pytest.mark.parametrize(
    ("fields", "changes"),
    [
        ({"event_type": EventType.OFFICIAL}, {"description": OFFICIAL_WALK_TEMPLATE}),
        ({"description": OFFICIAL_WALK_TEMPLATE}, {"event_type": "official"}),
    ],
)
def test_live_edit_refuses_official_with_unfilled_slots(test_user, make_event, fields, changes):
    event = make_event(**fields)
    assert _update_refused(test_user, event, changes).startswith("fill these template slots")


def test_edit_that_changes_nothing_is_refused(test_user, make_event):
    event = make_event(price="$20")
    event.tags.add(EventTag.objects.create(name="walk"))
    changes = {**PRICE, "tags": ["Walk"]}
    assert _update_refused(test_user, event, changes).startswith("nothing would change")


def test_preview_notes_side_effects(test_user, make_event, vettor_user):
    event = make_event(allow_plus_ones=True, max_attendees=1, rsvp_enabled=True)
    EventRSVP.objects.create(event=event, user=vettor_user, status=RSVPStatus.WAITLISTED)
    notes = _update(test_user, event, {"event_type": "club", "max_attendees": 5})["notes"]
    assert [note.split(" ")[0] for note in notes] == ["plus-ones", "raising"]
    assert _update(test_user, event, PRICE)["notes"] == []


def test_preview_notes_capacity_below_going(test_user, make_event, vettor_user):
    event = make_event(rsvp_enabled=True)
    EventRSVP.objects.create(event=event, user=vettor_user, status=RSVPStatus.ATTENDING)
    EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)
    notes = _update(test_user, event, {"max_attendees": 1})["notes"]
    assert len(notes) == 1 and notes[0].startswith("2 spots are already taken")
    assert _update(test_user, event, {"max_attendees": 2})["notes"] == []


def test_preview_notes_location_moved_without_new_pin(test_user, make_event):
    event = make_event(location="grand army plaza", latitude=40.67, longitude=-73.97)
    moved = {"location": "prospect park bandshell"}
    assert _update(test_user, event, moved)["notes"][0].startswith("the map pin stays")
    repinned = {**moved, "latitude": 40.66, "longitude": -73.97}
    assert _update(test_user, event, repinned)["notes"] == []
    unpinned = make_event(location="grand army plaza")
    assert _update(test_user, unpinned, moved)["notes"] == []


def test_preview_notes_non_member_removal(test_user, make_event):
    event = make_event(event_type=EventType.OFFICIAL, rsvp_enabled=True)
    for i, status in enumerate([RSVPStatus.ATTENDING, RSVPStatus.MAYBE]):
        guest = make_non_member(f"+1202555017{i}", f"n{i}@e.com")
        EventRSVP.objects.create(event=event, user=guest, status=status)
    to_community = {"event_type": "community"}
    asking = _update(test_user, event, to_community)["notes"]
    assert asking == [
        "removes 2 non-member rsvps and emails them: "
        "ask the user, then preview again with remove_non_member_rsvps true"
    ]
    forced = _update(test_user, event, to_community, remove_non_member_rsvps=True)["notes"]
    assert forced == ["removes 2 non-member rsvps and emails them"]
    assert _update(test_user, event, PRICE)["notes"] == []
    assert EventRSVP.objects.filter(event=event, status=RSVPStatus.REMOVED).count() == 0


def test_fields_outside_event_fields_are_ignored(test_user, make_event, vettor_user):
    event = make_event(EventStatus.DRAFT)
    slug = event.slug
    extra = {"status": "active", "slug": "taken-over", "co_host_ids": [str(vettor_user.pk)]}
    _update(test_user, event, {**PRICE, **extra})
    event.refresh_from_db()
    assert (event.price, event.status, event.slug) == ("$20", EventStatus.DRAFT, slug)
    assert list(event.co_hosts.all()) == [test_user]


def test_changes_schema_has_no_null_defaults(test_user):
    reset = _signed_in(test_user)
    tools = {tool.name: tool for tool in asyncio.run(pda_mcp.list_tools())}
    auth_context_var.reset(reset)
    schema = tools["update_event"].input_schema["$defs"]["EventChanges"]["properties"]
    assert not [name for name, field in schema.items() if "default" in field]
