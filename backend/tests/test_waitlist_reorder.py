"""Tests for host-driven waitlist reordering (Issue 1553)."""

import importlib

import pytest
from community._validation import Code
from community._waitlist import promote_from_waitlist
from community.models import Event, EventRSVP, RSVPStatus
from django.apps import apps as django_apps
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests._asserts import assert_error_code
from tests.conftest import future_iso


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


def _user(n):
    return User.objects.create_user(
        phone_number=f"+1202555{9200 + n}", password="x", first_name=f"U{n}"
    )


@pytest.fixture
def host(db):
    return _user(0)


@pytest.fixture
def full_event(db, host):
    event = Event.objects.create(
        title="Full Event",
        start_datetime=future_iso(days=14),
        rsvp_enabled=True,
        max_attendees=1,
        allow_plus_ones=True,
        created_by=host,
    )
    EventRSVP.objects.create(event=event, user=_user(1), status=RSVPStatus.ATTENDING)
    return event


@pytest.fixture
def waitlisted(full_event):
    users = [_user(n) for n in (2, 3, 4)]
    for u in users:
        EventRSVP.objects.create(event=full_event, user=u, status=RSVPStatus.WAITLISTED)
    return users


def _reorder(api_client, event, user, ids):
    return api_client.put(
        f"/api/community/events/{event.id}/waitlist/order/",
        {"user_ids": [str(i) for i in ids]},
        content_type="application/json",
        **_auth(user),
    )


def _waitlisted_guest_ids(response):
    return [g["user_id"] for g in response.json()["guests"] if g["status"] == RSVPStatus.WAITLISTED]


@pytest.mark.django_db
class TestReorderWaitlist:
    def test_host_reorders_and_guest_list_follows(self, api_client, full_event, host, waitlisted):
        a, b, c = waitlisted
        response = _reorder(api_client, full_event, host, [c.pk, a.pk, b.pk])
        assert response.status_code == 200
        assert _waitlisted_guest_ids(response) == [str(c.pk), str(a.pk), str(b.pk)]

    def test_promotion_follows_new_order(self, full_event, host, waitlisted, api_client):
        a, b, c = waitlisted
        _reorder(api_client, full_event, host, [b.pk, c.pk, a.pk])
        full_event.max_attendees = 2
        full_event.save()
        assert promote_from_waitlist(full_event) == [str(b.pk)]

    def test_new_joiner_goes_after_positioned_rows(self, api_client, full_event, host, waitlisted):
        a, b, c = waitlisted
        _reorder(api_client, full_event, host, [c.pk, b.pk, a.pk])
        late = _user(5)
        EventRSVP.objects.create(event=full_event, user=late, status=RSVPStatus.WAITLISTED)
        response = _reorder(api_client, full_event, host, [c.pk, b.pk, a.pk, late.pk])
        assert _waitlisted_guest_ids(response) == [str(c.pk), str(b.pk), str(a.pk), str(late.pk)]

    def test_leaving_waitlist_clears_position(self, api_client, full_event, host, waitlisted):
        a, b, c = waitlisted
        _reorder(api_client, full_event, host, [c.pk, a.pk, b.pk])
        rsvp = EventRSVP.objects.get(event=full_event, user=c)
        rsvp.status = RSVPStatus.CANT_GO
        rsvp.save(update_fields=["status"])
        rsvp.refresh_from_db()
        assert rsvp.waitlist_position is None

    def test_reorder_promotes_head_that_now_fits(self, api_client, full_event, host, waitlisted):
        a, b, c = waitlisted
        EventRSVP.objects.filter(event=full_event, user=a).update(has_plus_one=True)
        full_event.max_attendees = 2
        full_event.save()
        response = _reorder(api_client, full_event, host, [b.pk, a.pk, c.pk])
        assert response.status_code == 200
        assert EventRSVP.objects.get(event=full_event, user=b).status == RSVPStatus.ATTENDING

    def test_stale_list_rejected(self, api_client, full_event, host, waitlisted):
        a, b, _ = waitlisted
        response = _reorder(api_client, full_event, host, [b.pk, a.pk])
        assert response.status_code == 400
        assert_error_code(response, Code.Event.WAITLIST_ORDER_STALE)

    def test_duplicate_ids_rejected(self, api_client, full_event, host, waitlisted):
        a, b, c = waitlisted
        response = _reorder(api_client, full_event, host, [a.pk, a.pk, b.pk, c.pk])
        assert response.status_code == 400

    def test_non_host_forbidden(self, api_client, full_event, waitlisted):
        a, b, c = waitlisted
        response = _reorder(api_client, full_event, a, [a.pk, b.pk, c.pk])
        assert response.status_code == 403


@pytest.mark.django_db
class TestWaitlistPositionOnJoin:
    def test_joiners_get_sequential_positions(self, full_event, waitlisted):
        positions = [
            EventRSVP.objects.get(event=full_event, user=u).waitlist_position for u in waitlisted
        ]
        assert positions == [1, 2, 3]

    def test_rejoin_goes_to_end(self, full_event, waitlisted):
        a, _, _ = waitlisted
        rsvp = EventRSVP.objects.get(event=full_event, user=a)
        rsvp.status = RSVPStatus.CANT_GO
        rsvp.save(update_fields=["status"])
        rsvp.status = RSVPStatus.WAITLISTED
        rsvp.save(update_fields=["status"])
        rsvp.refresh_from_db()
        assert rsvp.waitlist_position == 4

    def test_update_or_create_assigns_position(self, full_event, waitlisted):
        late = _user(6)
        EventRSVP.objects.update_or_create(
            event=full_event, user=late, defaults={"status": RSVPStatus.WAITLISTED}
        )
        assert EventRSVP.objects.get(event=full_event, user=late).waitlist_position == 4

    def test_positions_are_per_event(self, full_event, host, waitlisted):
        other = Event.objects.create(
            title="Other", start_datetime=future_iso(days=14), rsvp_enabled=True, created_by=host
        )
        rsvp = EventRSVP.objects.create(
            event=other, user=waitlisted[0], status=RSVPStatus.WAITLISTED
        )
        assert rsvp.waitlist_position == 1


@pytest.mark.django_db
def test_backfill_numbers_existing_waitlists_in_line_order(full_event):
    backfill = importlib.import_module(
        "community.migrations.0097_backfill_waitlist_positions"
    ).backfill_positions
    users = [_user(n) for n in (7, 8, 9)]
    EventRSVP.objects.bulk_create(
        [EventRSVP(event=full_event, user=u, status=RSVPStatus.WAITLISTED) for u in users]
    )
    backfill(django_apps, None)
    positions = list(
        EventRSVP.objects.filter(event=full_event, status=RSVPStatus.WAITLISTED)
        .order_by("created_at", "pk")
        .values_list("waitlist_position", flat=True)
    )
    assert positions == [1, 2, 3]
